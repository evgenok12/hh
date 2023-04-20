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


def predict_rub_salary_sj(vacancy):
    if vacancy['currency'] != 'rub':
        return None
    if vacancy['payment_from'] and vacancy['payment_to']:
        return (vacancy['payment_from'] + vacancy['payment_to']) / 2
    if vacancy['payment_from']:
        return vacancy['payment_from'] * 1.2
    if vacancy['payment_to']:
        return vacancy['payment_to'] * 0.8 


def predict_rub_salary_hh(vacancy):
    salary = vacancy['salary']
    if not salary or salary['currency'] != 'RUR':
        return None
    if salary['from'] and salary['to']:
        return (salary['from'] + salary['to']) / 2
    if salary['from']:
        return salary['from'] * 1.2
    if salary['to']:
        return salary['to'] * 0.8 
        

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
        
        if payload['found'] <= 100:
            continue
        print(language)
        all_vacancies[language]['found'] = payload['found']
        all_vacancies[language]['items'] = []
        pages_number = payload['pages']
        print(f'Количество страниц: {pages_number}')

        while params['page'] < pages_number:
            page_response = requests.get(url, params)
            page_response.raise_for_status()
            page_payload = response.json()
            all_vacancies[language]['items'].extend(page_payload['items'])
            print(f"Страница {params['page'] + 1}/{pages_number} скачана")
            params['page'] = params.get('page') + 1
        print(f'{language} скачан', end='\n\n')

    for language, vacancies in all_vacancies.items():
        salaries = tuple(filter(lambda x: x, [predict_rub_salary_hh(vacancy) for vacancy in vacancies['items']]))      
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
        
        if payload['total'] <= 0:
            continue
        print(language)
        all_vacancies[language]['total'] = payload['total']
        all_vacancies[language]['objects'] = []
        pages_number = math.ceil(payload['total'] / params['count'])
        print(f'Количество страниц: {pages_number}')

        for _ in count(0):
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
            all_vacancies[language]['objects'].extend(payload['objects'])
            print(f"Страница {params['page'] + 1}/{pages_number} скачана")
            if not payload['more']:
                break
            params['page'] = params.get('page') + 1
        print(f'{language} скачан', end='\n\n')
    
    for language, vacancies in all_vacancies.items():
        salaries = tuple(filter(lambda x: x, [predict_rub_salary_sj(vacancy) for vacancy in vacancies['objects']]))      
        if not salaries:
            continue
        vacancies_summary[language] = {
            'vacancies_found': vacancies['total'],
            'vacancies_processed': len(salaries),
            'average_salary': int(sum(salaries) / len(salaries)),
        }

    return vacancies_summary


def create_table(vacancies_summary, title):
    table_data = [['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']]
    table_data.extend([language, *summary.values()] for language, summary in vacancies_summary.items())
    return AsciiTable(table_data, title).table


def main():
    env = Env()
    env.read_env()
    superjob_token = env('SUPERJOB_TOKEN')
    languages = (
        'Python', 'C++', 'Ruby', 'Delphi', '1С'
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
