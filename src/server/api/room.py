# -*- coding: UTF-8 -*-
# Common package
import msgpack
from flask import abort
from flask import request
from flask import jsonify
from flask import current_app as app
# Personal package
import util
from api import blueprint


@blueprint.route('/room')
def hello_room():
    return 'Hello room!'


@blueprint.route('/room/<string:identifier>/<string:semester>', methods=['GET'])
def get_room_schedule(identifier, semester):
    """
    通过教室资源ID和学期获取教室某学期的课程表
    :param identifier: 教室资源标识
    :param semester: 需要查询的学期
    :return: 该教室在该学期的课程
    """
    # 获取附加参数
    accept = request.values.get('accept')

    # 尝试解码教室资源标识
    try:
        id_type, id_code = util.identifier_decrypt(util.aes_key, identifier)
    except ValueError:
        abort(400, '查询的教室信息无法被识别')
        return

    # 检验数据的正确性
    if id_type != 'room' or util.check_semester(semester) is not True:
        abort(400, '查询的信息无法被识别')
        return

    # 从数据库中访问老师数据
    conn = app.mysql_pool.connection()
    with conn.cursor() as cursor:
        sql = """
        SELECT 
        `room`.`name` as room_name, 
        `room`.`building` as room_building, 
        `room`.`campus` as room_campus, 
        `card`.`name` as course_name,
        `card`.`klassID` as course_cid,
        `card`.`room` as course_room,
        `card`.`roomID` as course_rid,
        `card`.`week` as course_week,
        `card`.`lesson` as course_lesson,
        `teacher`.`name` as teacher_name,
        `teacher`.`title` as teacher_title,
        `teacher`.`code` as teacher_tid
        FROM `room_all` as room
        JOIN `card_%s` as card 
        ON room.code = card.roomID AND room.code = '%s'
        JOIN `teacher_link_%s` as t_link USING(cid)
        JOIN `teacher_%s` as teacher USING(tid);
        """ % (semester, id_code, semester, semester)
        cursor.execute(sql)
        result = cursor.fetchall()
        room_data = {}
        room_info = True
        course_info = {}
        for data in result:
            if room_info:
                room_info = False
                room_data['name'] = data[0]
                room_data['building'] = data[1]
                room_data['campus'] = data[2]
            if data[4] not in course_info:
                course_data = {
                    'name': data[3],
                    'cid': data[4],
                    'room': data[5],
                    'rid': data[6],
                    'week': data[7],
                    'lesson': data[8],
                    'teacher': []
                }
                course_info[data[4]] = course_data
            teacher_data = {
                'name': data[9],
                'title': data[10],
                'tid': data[11]
            }
            course_info[data[4]]['teacher'].append(teacher_data)
        # 将聚合后的数据转换为序列
        room_data['course'] = list(course_info.values())

    # 对资源编号进行对称加密
    for course in room_data['course']:
        course['cid'] = util.identifier_encrypt(util.aes_key, 'student', course['cid'])
        course['rid'] = util.identifier_encrypt(util.aes_key, 'student', course['rid'])
        for teacher in course['teacher']:
            teacher['tid'] = util.identifier_encrypt(util.aes_key, 'student', teacher['tid'])

    # 根据请求类型反馈数据
    if accept == 'msgpack':
        return msgpack.dumps(room_data)
    else:
        return jsonify(room_data)