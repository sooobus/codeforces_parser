import requests
import json
import random
import os
import logging

from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(filename="log.log", level=logging.ERROR)

class Downloader:
    def __init__(self, problems_complexity_interval, problems_counts, problems_tags, tests_folder="test/", sources_folder="source/"):
        self.complexity = problems_complexity_interval
        self.tags = problems_tags
        self.max_count = problems_counts
        self.tests_folder = tests_folder
        self.source_folder = sources_folder
        try:
            os.makedirs(tests_folder)
            os.makedirs(sources_folder)
        except:
            pass

    def dump(self, source, test_answers, contest_id, sub_id):
        tests_answers = [(t.split("\r\n")[:-1], a.split("\r\n")[:-1]) for t, a in test_answers]
        for i, el in enumerate(tests_answers):
            inp, outp = el
            base_filename = self.tests_folder + str(contest_id) + "_" + str(sub_id) + "_"
            with open(base_filename + str(i) + ".in", "w") as f:
                for l in inp:
                    f.write(l + "\n")
            with open(base_filename + str(i) + ".out", "w") as f:
                for l in outp:
                    f.write(l + "\n")
        with open(self.source_folder + str(contest_id) + "_" + str(sub_id) + ".cpp", "w") as f:
            f.write(source)

    def get_submission_texts(self):
        contest_sub_ids = self.get_submission_ids()
        print("Got {} submissions".format(len(contest_sub_ids)))
        print("Parsing submissions...")
        for contest_id, sub_id in tqdm(contest_sub_ids):
            page = requests.get("http://codeforces.com/contest/{}/submission/{}".format(contest_id, sub_id)) 
            if page.status_code == 200:
                try:
                    soup = BeautifulSoup(page.content, 'html.parser')
                    source = str(soup.find("pre", {"id": "program-source-text"}).string)
                    tests = []
                    answers = []
                    for inp in soup.find_all("div", {"class": "file input-view"}):
                        tests.append(str(inp.find("pre").string))
                    for outp in soup.find_all("div", {"class": "file output-view"}):
                        answers.append(str(outp.find("pre").string))
                    is_not_long = lambda t: t[0][-3:] != "..." and t[1][-3:] != "..." 
                    accepted = list(filter(is_not_long, zip(tests, answers)))
                    self.dump(source, accepted, contest_id, sub_id)
                except:
                    logging.error(str(contest_id) + "_" + str(sub_id))
                    logging.error(page.content)
        
    def get_submission_ids(self):
        problem_indices, contests = self.get_problems_with_contests()
        print("Got {} problems".format(len(problem_indices)))
        print("Extracting submissions...")
        all_submissions = []
        for problem_ind, contest_ind in tqdm(zip(problem_indices, contests)):
            successful = self.successful_submissions(contest_ind, problem_ind)
            all_submissions += successful
        return all_submissions

    def get_problems_with_contests(self):
        print("Getting some problems...")
        request = requests.get("http://codeforces.com/api/problemset.problems")
        json_ans = request.json()
        if json_ans['status'] == 'OK':
            problems = json_ans['result']['problems']
            problems = list(filter(lambda p: 'rating' in p and (self.complexity[0] <= p['rating'] < self.complexity[1]), problems))
            random.shuffle(problems)
            problems = problems[:min(self.max_count, len(problems))]
            contests = [p['contestId'] for p in problems]
            problems_indices = [p['index'] for p in problems]
            return problems_indices, contests
 
    def successful_submissions(self, contest_id, problem_id, count=100):
        request = requests.get("http://codeforces.com/api/contest.status?contestId={}&from=1&count={}".format(contest_id, count))
        json_ans = request.json()
        if json_ans['status'] == 'OK':
            submissions = json_ans['result']
            submissions = filter(lambda s: s['problem']['index'] == problem_id and 
                                           s['testset'] == "TESTS" and
                                           s['verdict'] == "OK" and
                                           s['programmingLanguage'].find("C++") != -1, submissions)
            submission_ids = [(contest_id, s['id']) for s in submissions]
            return submission_ids

d = Downloader([0, 10000], 100, [])
print(d.get_submission_texts())
