import os
import json
import copy
import traceback
import requests
import nltk

from ner.network import NER
from ner.corpus import Corpus
from ner.utils import lemmatize


class NerAgent:
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        self.kpi_name = self.config['kpi_name']
        self.agent = None
        self.session_id = None
        self.numtasks = None
        self.tasks = None
        self.observations = None
        self.agent_params = None
        self.predictions = None
        self.answers = None
        self.score = None
        self.response_code = None

    def init_agent(self):
        agent_config = self.config['kpis'][self.kpi_name]['settings_agent']
        model_dir = agent_config['model_dir']
        model_file = agent_config['model_file']
        dict_file = agent_config['dict_file']
        embedding_file = agent_config['embedding_file']

        params_path = os.path.join(model_dir, 'params.json')
        with open(params_path) as f:
            network_params = json.load(f)

        model_path = os.path.join(model_dir, model_file)
        dict_path = os.path.join(model_dir, dict_file)
        embeddingg_path = os.path.join(model_dir, embedding_file)

        corpus = Corpus(dicts_filepath=dict_path, embeddings_file_path=embeddingg_path)
        network = NER(corpus, pretrained_model_filepath=model_path, **network_params)
        self.agent = network

    def _set_numtasks(self, numtasks):
        self.numtasks = numtasks

    def _get_tasks(self):
        get_url = self.config['kpis'][self.kpi_name]['settings_kpi']['rest_url']
        if self.numtasks in [None, 0]:
            test_tasks_number = self.config['kpis'][self.kpi_name]['settings_kpi']['test_tasks_number']
        else:
            test_tasks_number = self.numtasks
        get_params = {'stage': 'netest', 'quantity': test_tasks_number}
        get_response = requests.get(get_url, params=get_params)
        tasks = json.loads(get_response.text)
        return tasks

    def _make_observations(self, tasks, human_input=False):
        observations = []
        if human_input:
            question = self._preprocess_humaninput(tasks[0])
            observations.append({
                'id': 'dummy',
                'input': nltk.tokenize.wordpunct_tokenize(tasks[0]),
                'question': question})
        else:
            for task in tasks['qas']:
                question = self._preprocess_task(task['question'])
                observations.append({
                    'id': task['id'],
                    'input': task['question'].split(' '),
                    'question': question})
        return observations

    def _preprocess_humaninput(self, task):
        tokens = nltk.tokenize.wordpunct_tokenize(task)
        return tokens

    def _preprocess_task(self, task):
        # tokens = tokenize(task)
        tokens = task.split(' ')
        tokens_lemmas = lemmatize(tokens)
        return tokens_lemmas

    def _get_predictions(self, observations):
        predictions = []
        for observation in observations:
            predict = self.agent.predict_for_token_batch([observation['question']])[0]
            # predict = ' '.join(self.agent.predict_for_token_batch([observation['question']])[0])
            predictions.append(predict)
        return predictions

    def _make_answers(self, observations, predictions, human_input=False):
        print(observations)
        print(predictions)
        answers = {}
        observ_predict = list(zip(observations, predictions))
        if human_input:
            for obs, pred in observ_predict:
                answers[obs['id']] = list(zip(obs['input'], pred))
            return answers['dummy']
        else:
            for obs, pred in observ_predict:
                answers[obs['id']] = ' '.join(pred)
            tasks = copy.deepcopy(self.tasks)
            tasks['answers'] = answers
            return tasks

    def _get_score(self, answers):
        post_headers = {'Accept': '*/*'}
        rest_response = requests.post(self.config['kpis'][self.kpi_name]['settings_kpi']['rest_url'],
                                      json=answers,
                                      headers=post_headers)
        return {'text': rest_response.text, 'status_code': rest_response.status_code}

    def _run_test(self):
        tasks = self._get_tasks()
        session_id = tasks['id']
        numtasks = tasks['total']
        self.tasks = tasks
        self.session_id = session_id
        self.numtasks = numtasks

        observations = self._make_observations(tasks)
        self.observations = observations

        predictions = self._get_predictions(observations)
        self.predictions = predictions

        answers = self._make_answers(observations, predictions)
        self.answers = answers

        score_response = self._get_score(answers)
        self.score = score_response['text']
        self.response_code = score_response['status_code']

    def _run_score(self, observation):
        observations = self._make_observations(observation, human_input=True)
        self.observations = observations
        predictions = self._get_predictions(observations)
        self.predictions = predictions
        answers = self._make_answers(observations, predictions, human_input=True)
        self.answers = answers

    def answer(self, input_task):
        try:
            if isinstance(input_task, list):
                print("%s human input mode..." % self.kpi_name)
                self._run_score(input_task)
                result = copy.deepcopy(self.answers)
                print("%s action result:  %s" % (self.kpi_name, result))
                return result
            elif isinstance(input_task, int):
                result = 'There is no NER EN ontonotes testing API provided'
                return result
            else:
                return {"ERROR": "{} parameter error - {} belongs to unknown type".format(self.kpi_name,
                                                                                          str(input_task))}
        except Exception as e:
            return {"ERROR": "{}".format(traceback.extract_stack())}
