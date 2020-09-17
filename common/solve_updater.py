from common.database import Database
from models.oj_model import OjModel, COLLECTION_NAME as OJ_COLLECTION_NAME
from models.user_model import UserModel, COLLECTION_NAME as USER_COLLECTION_NAME
from models.student_model import StudentModel, COLLECTION_NAME as BOOTCAMP_COLLECTION_NAME
from models.classroom_model import ClassroomModel
from scrappers.vjudge_sraper import profile_details as vjudge_details, solve_details_in_contest
from scrappers.cf_scrapper import profile_details as cf_details
from scrappers.loj_scrapper import profile_details as loj_details
from scrappers import vjudge_sraper
from common.OjMap import *

INF = 2 ** 100


def update_user_with_username(username):
    user = OjModel.get_by_username(username)
    oj_profiles = user.oj_info
    try:
        vjudge_data = vjudge_details(oj_profiles[VJUDGE][USERNAME])
    except:
        vjudge_data = {}
    for oj in vjudge_data:
        if oj not in oj_profiles:
            oj_profiles[oj] = {
                USERNAME: None,
                SOLVE_LIST: vjudge_data[oj]
            }
        else:
            oj_profiles[oj][SOLVE_LIST] = vjudge_data[oj]
        oj_profiles[oj][SOLVE_LIST] = [str(x) for x in oj_profiles[oj][SOLVE_LIST]]  # converting to list of strings

    update_json(oj_profiles, CODEFORCES, cf_details)
    update_json(oj_profiles, LIGHTOJ, loj_details)

    user.update_to_mongo({"oj_info": oj_profiles})


def update_json(oj_profiles, oj_name, arg):
    if oj_name in oj_profiles and oj_profiles[oj_name]:
        solve_list_data = arg(oj_profiles[oj_name][USERNAME])
        solve_list_data = [str(x) for x in solve_list_data]  # converting to list of strings
        if SOLVE_LIST in oj_profiles[oj_name] and oj_profiles[oj_name][SOLVE_LIST]:
            oj_profiles[oj_name][SOLVE_LIST].extend(solve_list_data)
        else:
            oj_profiles[oj_name][SOLVE_LIST] = solve_list_data
        oj_profiles[oj_name][SOLVE_LIST] = list(set(oj_profiles[oj_name][SOLVE_LIST]))


def update_all():
    user_list = Database.get_all_records("users")
    for user in user_list:
        update_user_with_username(user[USERNAME])


def bootcamp_update_one(username):
    user = UserModel.get_by_username(username)
    classroom = ClassroomModel.get_by_classroom_name(user.classroom_name)
    bootcamp = StudentModel.get_by_username(username)
    if not bootcamp:
        bootcamp = StudentModel(username=username, bootcamp_name=user.classroom_name)
    if not classroom:
        return

    vjudge_handle = OjModel.get_by_username(username).oj_info[VJUDGE][USERNAME]
    long_contests = []
    for contest in classroom.vjudge_contest_list:
        long_contests.append({
            "contest_title": contest["contest_title"],
            "total_problems": contest["total_problems"],
            "minimum_solve_required": contest["minimum_solve_required"],
            "solved_problems": solve_details_in_contest(contest_id=contest["contest_id"], username=vjudge_handle)
        })
    data = {
        "long_contests": long_contests
    }
    print(data)
    bootcamp.update_to_mongo(data)


def bootcamp_update_all():
    user_list = Database.get_all_records("users")
    for user in user_list:
        bootcamp_update_one(user[USERNAME])


def update_students(classroom):
    data_map = {}
    for contest in classroom.vjudge_contest_list:
        data_map[contest["contest_id"]] = vjudge_sraper.get_contest_details_data(contest["contest_id"])
    for username in classroom.user_list:
        vjudge_handle = None
        try:
            vjudge_handle = OjModel.get_by_username(username).oj_info[VJUDGE][USERNAME]
        except:
            continue
        student = StudentModel.get_by_username_and_classroom_name(username, classroom.classroom_name)
        long_contests = []
        for contest in classroom.vjudge_contest_list:
            long_contests.append(
                {
                    "contest_title": contest["contest_title"],
                    "total_problems": contest["total_problems"],
                    "minimum_solve_required": contest["minimum_solve_required"],
                    "solved_problems": vjudge_sraper.solve_details_in_contest_from_data(
                        data=data_map[contest["contest_id"]],
                        username=vjudge_handle),
                    "contest_type": contest["contest_type"]
                }
            )
        new_values = {
            "long_contests": long_contests
        }
        student.update_to_mongo(new_values)


def get_rank_list_live(user_list, contest_list, start_time, end_time, contest_data=None):
    header = ["username"]
    data_map = {}
    for contest in contest_list:
        if contest_data:
            data = contest_data[contest["contest_id"]]
        else:
            data = vjudge_sraper.get_contest_details_data(contest["contest_id"])
        data_map[contest["contest_id"]] = data
        header.append(vjudge_sraper.get_contest_name_from_data(data))
    header.append("Total Solve")

    rank_list = []
    for username in user_list:
        vjudge_handle = None
        solve_list = [username]
        total_solve = 0
        try:
            vjudge_handle = OjModel.get_by_username(username).oj_info[VJUDGE][USERNAME]
        except:
            continue
        for contest in contest_list:
            solve_count = vjudge_sraper.solve_details_in_contest_from_data_with_timestamp(
                data=data_map[contest["contest_id"]],
                username=vjudge_handle,
                end_time=end_time,
                start_time=start_time
            )
            total_solve += solve_count
            solve_list.append(int(solve_count))
        solve_list.append(total_solve)
        rank_list.append(solve_list)

    rank_list = sorted(rank_list, key=lambda row: row[len(row) - 1], reverse=True)
    rank_list.insert(0, header)
    return rank_list


# def update_contest_data():
#     classroom_list = ClassroomModel.get_all_classrooms()
#     contest_data = {}
#     for classroom in classroom_list:


if __name__ == '__main__':
    Database.initialize()
    bootcamp_update_one("bashem")
