import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import  tool
from datetime import datetime
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.sheets import SheetsClient


SHEETS = SheetsClient()


def get_llm(temperature: float = 0.3):
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=temperature,
    )


@tool
def get_expert_analyze(
    project_name: str = "",
    employee: str = "",
    technology: str = "",
    source: str = "",
    grade: str = "",
    date: str = ""
) -> str:
    """
    Используй этот инструмент, чтобы получить анализ от эксперта кандидата, если он есть.

    Входные параметры:
    project_name: str - название проекта, если доступно.
    employee: str - имя кандидата, если доступно.
    technology: str - технология, на которую собеседовался кандидат.
    source: str - откуда кандидат.
    grade: str - грейд кандидата.
    date: str - дата интервью.
    """
    filtered_data = SHEETS.list_case_options(filters={
        'project_name': project_name,
        'employee': employee,
        'technology': technology,
        'source': source,
        'grade': grade,
        'date': date
    }).items
    if len(filtered_data) > 1:
        return 'Найдено более одной записи для таких данных, уточни какие нужны: ' + str(filtered_data)
    elif len(filtered_data) == 0:
        return 'Не найдена запись для таких входных данных'
    case = filtered_data[0]
    if 'http' in case.expert_analyze:
        try:
            return SHEETS.extract_expert_analyze(case.expert_analyze)
        except:
            return 'Не удалось загрузить анализ'
    else: 
        return case.expert_analyze


@tool
def get_available_months() -> list[str]:
    '''Используй этот инструмент чтобы узнать за какие месяцы доступны разборы'''
    return list(SHEETS.sheets.keys())


@tool
def get_month_cases(month: str = "", query: str = "", limit: int = 200) -> str:
    '''
    Используй этот инструмент, для того чтобы найти кейсы за месяц или выполнить
    аналитический запрос к таблице.
    Не используй этот инструмент для поиска информации за месяц, который ещё не наступил.
    
    Входные параметры:
    month: str - название месяца. Январь, Февраль и т.д. Если пусто или "all", поиск по всем месяцам.
    query: str - pandas query выражение для фильтрации строк и столбцов. Примеры:
        technology == "Python"
        grade.str.contains("senior", case=False, na=False)
        source != "" and project_name.str.contains("bank", case=False, na=False)
    limit: int - максимум строк в ответе, от 1 до 300.


    Столбцы в таблице:
    spc - имя координатора
    project_name - название проекта
    employee - имя кандидата
    technology - технология кандидата
    grade - какой грейд у кандидата
    source - откуда кандидат
    commentary - комментарий от координатора
    expert_analyze - анализ эксперта
    readiness - готовность кандидата по оценкам с интревью от независимых экспертов
    date - дата собеседования с заказчиком
    '''
    try:
        month_key = month.strip()
        if not month_key or month_key.lower() == "all":
            data = SHEETS.get_all_cases()
        else:
            sheets_by_lower = {name.lower(): name for name in SHEETS.sheets}
            sheet_name = sheets_by_lower.get(month_key.lower(), month_key)
            data = SHEETS.sheets[sheet_name]

        data = data.drop(columns=['demand'], errors='ignore').fillna("")

        if query.strip():
            data = data.query(query, engine="python")

        safe_limit = min(max(int(limit), 1), 1000)
        analytics_columns = [
            "sheet",
            "project_name",
            "technology",
            "grade",
            "source",
            "readiness",
        ]
        analytics = {
            column: data[column].astype(str).str.strip().loc[lambda values: values != ""].value_counts().head(20).to_dict()
            for column in analytics_columns
            if column in data.columns
        }
        result = {
            "matched_rows": int(len(data)),
            "returned_rows": int(min(len(data), safe_limit)),
            "columns": list(data.columns),
            "analytics": analytics,
            "rows": data.head(safe_limit).to_dict("records"),
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return f'Не удалось выполнить запрос: {e}. Доступные месяца: ' + ', '.join(SHEETS.sheets.keys())


@tool
def get_case( 
    project_name: str = "",
    employee: str = "",
    technology: str = "",
    source: str = "",
    grade: str = "",
    date: str = ""
    ):
    '''
    Используй этот инструмент, чтобы найти конкретный кейс по доступным данным
    
    Входные параметры опциональны:
    project_name: str - название проекта, если доступно.
    employee: str - имя кандидата, если доступно.
    technology: str - технология, на которую собеседовался кандидат.
    source: str - откуда кандидат.
    grade: str - грейд кандидата.
    date: str - дата интервью.
    '''
    
    return SHEETS.list_case_options(filters={
        'project_name': project_name,
        'employee': employee,
        'technology': technology,
        'source': source,
        'grade': grade,
        'date': date
    }).items



def get_agent(
        context: str = 'Нет дополнительной информации', 
        tools: list = [get_case, get_month_cases, get_expert_analyze, get_available_months]
    ):
    today = datetime.now().strftime("%d/%m/%Y")

    prompt = ChatPromptTemplate.from_messages([
    ("system", f"""Сегодня {today}.
Ты анализируешь кейсы с отказами кандидатам от заказчиков после интервью \
и отвечаешь на вопросы пользователя. Все данные что ты будешь видеть - это данные с отказами.
Если нужно проанализировать конкретных кандидатов, \
то ОБЯЗАТЕЛЬНО смотри на анализ экспертов.
Дополнительная информация может быть представлена ниже:
{context}
"""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
    ])
    agent =  create_tool_calling_agent(
        llm=get_llm(),
        tools=tools,
        prompt=prompt
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
