import requests
import random
import os
import logging
import time

from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(filename="log.log", level=logging.ERROR)

class Downloader:
    def __init__(self, problems_complexity_interval, problems_counts, tests_folder="test/", sources_folder="source/"):
        self.complexity = problems_complexity_interval
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

    def ask_codeforces(self, request_text):
        time.sleep(0.2)
        page = requests.get(request_text)
        if page.status_code == 200:
            return page
        elif page.status_code == 403:
            return None
        else:
            raise Exception("Couldn't interact with Codeforces: status {}".format(page.status_code))

    def get_submission_texts(self):
        contest_sub_ids = self.get_submission_ids()
        print("Got {} submissions".format(len(contest_sub_ids)))
        print("Parsing submissions...")
        for contest_id, sub_id in tqdm(contest_sub_ids):
            page = self.ask_codeforces("http://codeforces.com/contest/{}/submission/{}".format(contest_id, sub_id))
            if page:
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
        request = self.ask_codeforces("http://codeforces.com/api/problemset.problems")
        if request:
            json_ans = request.json()
            problems = json_ans['result']['problems']
            problems = list(filter(lambda p: 'rating' in p and (self.complexity[0] <= p['rating'] < self.complexity[1]), problems))
            random.shuffle(problems)
            problems = problems[:min(self.max_count, len(problems))]
            contests = [p['contestId'] for p in problems]
            problems_indices = [p['index'] for p in problems]
            return problems_indices, contests

    def successful_submissions(self, contest_id, problem_id, count=1000):
        request = self.ask_codeforces("http://codeforces.com/api/contest.status?contestId={}&from=1&count={}".format(contest_id, count))
        if request:
            json_ans = request.json()
            submissions = json_ans['result']
            submissions = filter(lambda s: s['problem']['index'] == problem_id and 
                                           s['testset'] == "TESTS" and
                                           s['verdict'] == "OK" and
                                           s['programmingLanguage'].find("C++") != -1, submissions)
            submission_ids = [(contest_id, s['id']) for s in submissions]
            return submission_ids

if __name__ == "__main__":
    d = Downloader([0, 10000], 100)
    print(d.get_submission_texts())
