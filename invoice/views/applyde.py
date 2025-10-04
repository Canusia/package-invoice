import csv, io, logging, requests, datetime, json
from django.conf import settings

from cis.models.sis import SIS_Log
from cis.settings.sis_settings import sis_settings

logger = logging.getLogger(__name__)

class ApplyDE:
    URL = 'https://applyde.laregents.edu/'
    # URL = 'https://highschool.rmu.edu/'
    # URL = 'http://127.0.0.1:8002/'
    # APPLYDE_USERNAME = settings.APPLYDE_USERNAME
    # APPLYDE_PASSWORD = settings.APPLYDE_PASSWORD

    APPLYDE_USERNAME = "kadaji@gmail.com"
    APPLYDE_PASSWORD = "kryGkin9318!"

    def get_auth_token(self):
        # Implementation for obtaining authentication token
        url = self.URL + "api/auth/token/login/"
        response = requests.post(url, data={'username': self.APPLYDE_USERNAME, 'password': self.APPLYDE_PASSWORD})
        if response.status_code == 200:
            return response.json().get('auth_token')
        else:
            logger.error(f"Failed to obtain auth token: {response.text}")
            return None

    def get_registrations(self, term_id=None, sau=None, sau_type='student_highschool', group_by=None):
        url = self.URL + f"ce/api/registration/?term={term_id}&group_by={group_by}"
        if sau:
            url += f"&sau={sau}"
        if sau_type:
            url += f"&sau_type={sau_type}"

        headers = {'Authorization': f'Token {self.get_auth_token()}'}

        all_results = []
        while url:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if 'results' in result:
                    all_results.extend(result['results'])
                else:
                    all_results.extend(result if isinstance(result, list) else [result])
                url = result.get('next')
            else:
                logger.error(f"Failed to fetch registrations: {response.text}")
                break
        return all_results

    def get_terms(self, campus_code='EV234'):
        url = self.URL + f"ce/api/term/?campus_code={campus_code}"

        headers = {'Authorization': f'Token {self.get_auth_token()}'}
        
        all_results = []
        
        while url:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                # Add results from current page
                if 'results' in result:
                    all_results.extend(result['results'])
                else:
                    all_results.extend(result if isinstance(result, list) else [result])
                
                url = result.get('next')                
            else:
                logger.error(f"Failed to fetch terms: {response.text}")
                break
        
        return all_results

    def get_terms_pretty(self, campus_code='EV234'):
        terms = self.get_terms(campus_code=campus_code)
        pretty_terms = []

        for term in terms:
            pretty_terms.append((term.get('id'), term.get('label')))
        return pretty_terms