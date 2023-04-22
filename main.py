import requests
from collections import defaultdict
from itertools import count
import math
from terminaltables import AsciiTable
from environs import Env


HH_ROLE_ID = 96
SJ_ROLE_ID = 48
HH_TOWN_ID = 1
SJ_TOWN_ID = 4
VACANCIES_PER_PAGE = 100
FIRST_PAGE_NUMBER = 0
HH_MIN_VACANTIONS_NUMBER = 100


def predict_rub_salary_hh(vacancy):
    if vacancy['salary']['currency'] != 'RUR':
        return None
    return predict_rub_salary(vacancy['salary']['from'], vacancy['salary']['to'])


def predict_rub_salary_sj(vacancy):
    if vacancy['currency'] != 'rub':
        return None
    return predict_rub_salary(vacancy['payment_from'], vacancy['payment_to']) 


def predict_rub_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    if salary_from:
        return salary_from * 1.2
    if salary_to:
        return salary_to * 0.8 


def get_vacancies_summary_hh(languages):
    url = 'https://api.hh.ru/vacancies/'
    vacancies_summary = {}
    all_vacancies = defaultdict(dict)

    for language in languages:
        params = {
            'text': language,
            'professional_role': HH_ROLE_ID,
            'area': HH_TOWN_ID,
            'per_page': VACANCIES_PER_PAGE,
            'page': FIRST_PAGE_NUMBER,
        }
        response = requests.get(url, params)
        response.raise_for_status()
        payload = response.json()
        
        if payload['found'] <= HH_MIN_VACANTIONS_NUMBER:
            continue
        print(language)
        all_vacancies[language]['found'] = payload['found']
        all_vacancies[language]['items'] = []
        pages_number = payload['pages']
        print(f'Количество страниц: {pages_number}')

        for _ in count(0):     
            all_vacancies[language]['items'] += payload['items']
            print(f"Страница {params['page'] + 1}/{pages_number} скачана")
            if params['page'] == pages_number - 1:
                break
            params['page'] += 1
            response = requests.get(url, params)
            response.raise_for_status()
            payload = response.json()

        print(f'{language} скачан', end='\n\n')

    for language, vacancies in all_vacancies.items():
        salaries = tuple(filter(lambda x: x,
        [predict_rub_salary_hh(vacancy) for vacancy in vacancies['items'] if vacancy['salary']]
        ))

        if not salaries:
            continue
        vacancies_summary[language] = {
            'vacancies_found': vacancies['found'],
            'vacancies_processed': len(salaries),
            'average_salary': int(sum(salaries) / len(salaries)),
        }

    return vacancies_summary


def get_vacancies_summary_sj(languages, token):
    url = 'https://api.superjob.ru/2.0/vacancies/'
    headers = {'X-Api-App-Id': token, }
    vacancies_summary = {}
    all_vacancies = defaultdict(dict)

    for language in languages:
        params = {
            'keyword': language,
            'catalogues': SJ_ROLE_ID,
            'town': SJ_TOWN_ID,
            'count': VACANCIES_PER_PAGE,
            'page': FIRST_PAGE_NUMBER,
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        
        if not payload['total']:
            continue
        print(language)
        all_vacancies[language]['total'] = payload['total']
        all_vacancies[language]['objects'] = []
        pages_number = math.ceil(payload['total'] / params['count'])
        print(f'Количество страниц: {pages_number}')

        for _ in count(0):
            all_vacancies[language]['objects'] += payload['objects']
            print(f"Страница {params['page'] + 1}/{pages_number} скачана")
            if not payload['more']:
                break
            params['page'] += 1
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()  

        print(f'{language} скачан', end='\n\n')
    
    for language, vacancies in all_vacancies.items():
        salaries = tuple(filter(lambda x: x, 
        [predict_rub_salary_sj(vacancy) for vacancy in vacancies['objects']]
        ))      

        if not salaries:
            continue
        vacancies_summary[language] = {
            'vacancies_found': vacancies['total'],
            'vacancies_processed': len(salaries),
            'average_salary': int(sum(salaries) / len(salaries)),
        }

    return vacancies_summary


def create_table(vacancies_summary, title):
    table = [
        ['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']
        ]
    table.extend(
        [language, *summary.values()] for language, summary in vacancies_summary.items()
        )
    return AsciiTable(table, title).table


def main():
    env = Env()
    env.read_env()
    superjob_token = env('SUPERJOB_TOKEN')
    languages = (
        'Python', 'C++', 'Java', 'C#', 'JavaScript', 'PHP', 'Swift', 'Go',
        'Scala', 'TypeScript', 'Kotlin', 'Rust', 'Ruby', 'Delphi', '1С'
        )
    print('Скачиваем вакансии с hh')
    vacancies_summary_hh = get_vacancies_summary_hh(languages)
    print('Вакансии с hh скачаны', end='\n\n')
    print('Скачиваем вакансии с sj')
    vacancies_summary_sj = get_vacancies_summary_sj(languages, superjob_token)
    print('Вакансии с sj скачаны', end='\n\n')
    print(create_table(vacancies_summary_hh, 'HeadHunter Moscow'), end='\n\n')
    print(create_table(vacancies_summary_sj, 'SuperJob Moscow'))


if __name__  == '__main__':
    main() 
