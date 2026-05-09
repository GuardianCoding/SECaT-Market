import json
import re
import request_secat_data


def outToData(courseName: str, sem: int, year: int, questionNum: int):


    contents = request_secat_data.getCourseData(courseName, sem, year)

    match = re.search(r"courseSECATData\s*=\s*(\[.*\])\s*;", contents, re.DOTALL)

    if not match:
        raise ValueError("Could not find courseSECATData array in the file")

    json_text = match.group(1)

    courseSECATData = json.loads(json_text)

    q_results = [
        item for item in courseSECATData
        if item["QUESTION_NAME"].startswith(f"Q{questionNum}")
    ]

    q_results = sorted(q_results, key=lambda x: int(x["ANSWER"].split()[0]))
    return q_results

courses = ['comp3301', 'csse1001']

for course in courses:
    print(f"results for {course}")
    q8_results = outToData(course, 2, 2024, 3)
    for result in q8_results:
        print(
            result["ANSWER"],
            "- Count:",
            result["VALUE"],
            "- Percent:",
            round(result["PERCENT_ANSWER"], 2),
            "%"
        )

