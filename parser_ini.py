# -*- coding:utf-8 -*-

"""
解析当前目录下的 ini 文件
    A)生成单个pac 的打包配置文件。
    B)打包是否带运营商，并列出。
    C)编译工程是否需要做ota,且提供出 modem 获取路径。

调用方法：
    A)没有运营商信息：
    python parser_ini.py --project "project" --board "board" --out "out_dir"

    B)有运营商信息：
    python parser_ini.py --project "project" --board "board" --out "out_dir" --carrier "carriers"

    project  Eg:s9863a1h10_Natv-userdebug-gms
    board    Eg:s9863a1h10
    out      :out目录绝对路径。
    carrier  :运营商名,多个运营商之间用空格分隔。
"""

import os
import sys
import codecs
import optparse
#import ConfigParser


try:
    # Python3
    from configparser import ConfigParser
except ImportError:
    # Python2
    from ConfigParser import ConfigParser



OTA_CARRIER_FLAG_FILE = 'ota_carrier_flag'
PAC_CFG_FILE = 'pac.ini'
PAC_SECTION = 'pac_list'


def help(args):
    init_optparse = optparse.OptionParser(
        usage="usage: %prog [options] arg",
        description="show help")
    init_optparse.add_option(
        '--project',
        help='project name',
        metavar='version',
        dest='project')
    init_optparse.add_option(
        '--board',
        help='board name',
        metavar='version',
        dest='board')
    init_optparse.add_option(
        '--out',
        help='out directory',
        metavar='version',
        dest='out')
    init_optparse.add_option(
        '--carriers',
        help='carriers info',
        metavar='version',
        dest='carriers')

    (options, args) = init_optparse.parse_args(args)

    if options.project:
        return (options, args)
    else:
        print("please check your params")
        return (None, args)


def create_pac_cfg(cfg_file, project, out_dir, carriers=None):
    """
    生成mini cfg file
    :param cfg_file:out_dir
    :param project:
    :param carriers:
    :return:
    """

    settings_info = ''

    if not os.path.exists(cfg_file):
        print("cfg file not exist!")
        print("cp_sign_fail")
        sys.exit(1)

    cfg_parser = BMConfigParser()
    cfg_parser.read(cfg_file)

    # [Setting]字段内容
    with open(cfg_file, 'r') as fp:
        for line in fp:
            if '[project]' not in line:
                settings_info += line
            else:
                break

    ######## Settings ##########
    #settings_info = "[Setting]\n"
    #for (k, v) in cfg_parser.items('Setting'):
    #    settings_info +="%s=%s\n" % (k,v)

    ######### WORK_DIR/PAC_NAME #######
    py_path = os.path.abspath(os.path.dirname(__file__))
    config_ini_path = os.path.abspath(os.path.join(py_path,'..','pac_config','config.ini'))
    common_parser = BMConfigParser()
    common_parser.read(config_ini_path)

    cfg_work_dir = common_parser.get('work_dir','dir').strip()
    if cfg_work_dir:
        work_dir = py_path.split(cfg_work_dir)[0]
    else:
        work_dir = py_path
        
    #if 'vendor' in py_path:
    #    work_dir = py_path[0:py_path.rindex('vendor')]
    #else:
    #    work_dir = py_path
    print("work dir : ",work_dir)
    work_dir_line = "%s" % work_dir

    carrier_partitions = cfg_parser.get(
        "partition", "carrier_partition").strip().split(',')

    prj_ops = cfg_parser.options('project')
    print("projects in cfg :",prj_ops)
    print("current project : ", project)
    if project not in prj_ops:
        print("No project : %s. Please check! " % project)
        print("cp_sign_fail")
        sys.exit(1)
    project_info = cfg_parser.get('project', project).strip().split('\n')
    print project_info
    if not project_info:
        print("Project : %s not in config file!" % project)
        print("cp_sign_fail")
        sys.exit(1)

    if carriers:  # 有运营商
        exist_ca = False
        for ca in carriers.split(' '):
            if ca in cfg_parser.get('project', project):
                print("Carrier: %s  in project %s !" % (ca, project))
                exist_ca = True
        if not exist_ca:  # 该project中不存在 carrier值
            print("No carrier in project!! Please check!")
            print("cp_sign_fail")
            sys.exit(1)

        ########## 存在 carrier, 遍历 ###########
        for ca in carriers.split(' '):
            no_ca = True
            for content in project_info:
                pac_info = ''
                if ca in content:
                    no_ca = False
                    print("Carrier: %s in : %s !" % (ca, content))
                    modem_type = content.split('@')[0]
                    if ":" in modem_type:  # 类似这样的字符串： HARKL3_9863A_9_GSI:ota@xx
                        # ota_flag = modem_type.split(':')[1]  # ota flag
                        modem_type = modem_type.split(':')[0]

                    # 从配置文件中获取 modem_type字段的值
                    for (k, v) in cfg_parser.items(modem_type):
                        # carrier 分区
                        if k in carrier_partitions:
                            last_data = str(v).strip().split('/')[-1]
                            v = str(v).split(last_data)[0]
                            v = os.path.join(v, ca, last_data)
                        line = "%s=%s\n" % (k, v)
                        pac_info += line

                    carrier_info_list = content.split(
                        '@')[1].split('|')  # ca1:ota1|ca2:ota2
                    for info in carrier_info_list:
                        if ':' in info:  # carrier:ota
                            ota_flag = info.split(':')[1]
                            carrier = info.split(':')[0]
                            if ota_flag == 'ota':
                                ota_flag = 'true'
                            else:
                                ota_flag = 'false'
                        else:
                            carrier = info.strip()
                            ota_flag = 'false'

                        if ca == carrier:
                            # 创建以modem type和运营商名称为名字的文件夹
                            dirs = os.path.join(
                                out_dir, "%s_%s" %
                                (modem_type, ca))
                            if not os.path.exists(dirs):
                                os.makedirs(dirs)
                            pac_name_line = "%s_%s_%s.pac" % (project,modem_type,ca)
                            create_file(dirs,ca,ota_flag, settings_info, pac_info)

                            parser = BMConfigParser()
                            with codecs.open(os.path.join(dirs, PAC_CFG_FILE),'r') as pf:
                                parser.read(pf)
                            parser.add_section("Attr")
                            parser.set("Attr","PAC_NAME",pac_name_line)
                            parser.set("Attr", "WORK_DIR", work_dir_line)
                            parser.set("Attr", "ota_flag", ota_flag)
                            parser.set("Attr", "carrier", ca)
                            with codecs.open(os.path.join(dirs, PAC_CFG_FILE),'a', encoding='utf-8') as f:
                                parser.write(f)

                    #####################default ######################
                    pac_info = ''
                    dirs = os.path.join(out_dir, "%s" %(modem_type))
                    if not os.path.exists(dirs):
                        os.makedirs(dirs)
                    ota_flag = 'false'
                    if ":" in content.split('@')[0]:  # 类似这样的字符串： HARKL3_9863A_9_GSI:ota@xx
                        ota_flag = content.split('@')[0].split(':')[1]  # ota flag
                        if ota_flag == 'ota':
                            ota_flag = 'true'
                        else:
                            ota_flag = 'false'
                    pac_name_line = "%s_%s.pac" % (project,modem_type)
                    for (k, v) in cfg_parser.items(modem_type):
                        line = "%s=%s\n" % (k, v)
                        pac_info += line
                    create_file(dirs, '', ota_flag, settings_info, pac_info)
                    parser = BMConfigParser()
                    parser.add_section("Attr")
                    with codecs.open(os.path.join(dirs, PAC_CFG_FILE), 'r') as pf:
                        parser.read(pf)
                    parser.set("Attr", "PAC_NAME", pac_name_line)
                    parser.set("Attr", "WORK_DIR", work_dir_line)
                    parser.set("Attr","ota_flag",ota_flag)
                    parser.set("Attr","carrier",'')
                    with codecs.open(os.path.join(dirs, PAC_CFG_FILE), 'a', encoding='utf-8') as f:
                        parser.write(f)

                else:
                    ota_flag = 'false'
                    pac_info = ''
                    modem_type = content.split('@')[0]
                    print("modem type :", modem_type)
                    if ":" in modem_type:  # 类似这样的字符串： HARKL3_9863A_9_GSI:ota@xx
                        ota_flag = modem_type.split(':')[1]  # ota flag
                        modem_type = modem_type.split(':')[0]
                        if ota_flag == 'ota':
                            ota_flag = 'true'
                        else:
                            ota_flag = 'false'

                    # 从配置文件中获取 modem_type字段的值
                    for (k, v) in cfg_parser.items(modem_type):
                        line = "%s=%s\n" % (k, v)
                        pac_info += line

                    dirs = os.path.join(
                        out_dir, "%s" %
                                 modem_type)  # cp_sign/ ota_sign
                    if not os.path.exists(dirs):
                        os.makedirs(dirs)

                    #settings_info += '\n'
                    pac_name_line = "%s_%s.pac" % (project, modem_type)
                    #settings_info += '\n'
                    create_file(dirs,'', ota_flag, settings_info, pac_info)
                    parser = BMConfigParser()
                    with codecs.open(os.path.join(dirs, PAC_CFG_FILE), 'r') as pf:
                        parser.read(pf)
                    parser.add_section("Attr")
                    parser.set("Attr", "PAC_NAME", pac_name_line)
                    parser.set("Attr", "WORK_DIR", work_dir_line)
                    parser.set("Attr","ota_flag",ota_flag)
                    parser.set("Attr","carrier",'')
                    with codecs.open(os.path.join(dirs, PAC_CFG_FILE), 'a', encoding='utf-8') as f:
                        parser.write(f)
            if no_ca:
                print("Carrier : %s not in config file! Please check!" % ca)
    else:  # 没有运营商
        for content in project_info:
            print(content)
            ota_flag = 'false'
            pac_info = ''
            modem_type = content.split('@')[0]
            print("modem type :", modem_type)
            if ":" in modem_type:  # 类似这样的字符串： HARKL3_9863A_9_GSI:ota@xx
                ota_flag = modem_type.split(':')[1]  # ota flag
                modem_type = modem_type.split(':')[0]
                if ota_flag == 'ota':
                    ota_flag = 'true'
                else:
                    ota_flag = 'false'

            # 从配置文件中获取 modem_type字段的值
            for (k, v) in cfg_parser.items(modem_type):
                line = "%s=%s\n" % (k, v)
                pac_info += line

            dirs = os.path.join(
                out_dir, "%s" %
                modem_type)  # cp_sign/ ota_sign
            if not os.path.exists(dirs):
                os.makedirs(dirs)
            pac_name_line = "%s_%s.pac" % (project, modem_type)

            create_file(dirs,'',ota_flag,settings_info,pac_info)
            parser = BMConfigParser()
            with codecs.open(os.path.join(dirs, PAC_CFG_FILE), 'r') as pf:
                parser.read(pf)
            parser.add_section("Attr")
            parser.set("Attr", "PAC_NAME", pac_name_line)
            parser.set("Attr","WORK_DIR",work_dir_line)

            parser.set("Attr", "ota_flag", ota_flag)
            parser.set("Attr", "carrier", '')

            with codecs.open(os.path.join(dirs, PAC_CFG_FILE), 'a', encoding='utf-8') as f:
                parser.write(f)

    if os.path.exists(out_dir):
        os.chdir(out_dir)
        sys.stdout.flush()
        os.system('tree')

def create_file(dirs,carrier,ota_flag,settings_info,pac_info):
    #################### 生成 pac.ini 和 flag文件 ########################
    #with open(os.path.join(dirs, OTA_CARRIER_FLAG_FILE), 'w') as flg:
    #    flg.writelines("ota_flag=%s\n" % ota_flag)
    #    flg.writelines("carrier=%s" % carrier)

    with open(os.path.join(dirs, PAC_CFG_FILE), 'w') as cf:
        cf.writelines(settings_info)
        cf.writelines('\n')
        cf.writelines('[%s]' % PAC_SECTION)
        cf.writelines('\n')
        cf.writelines(pac_info)
        cf.writelines('\n')

class BMConfigParser(ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, option_str):
        return option_str


if __name__ == '__main__':
    args = sys.argv[1:]
    (options, args) = help(args)
    if args is None:
        print("Parameter error! Parameter is None! Please check!")
        print("cp_sign_fail")
        sys.exit(1)

    print("====================== parser_ini start ==============================")
    project = options.project
    out_dir = options.out
    board = options.board
    carriers = options.carriers if options.carriers else ''
    carriers = carriers.strip()

    file_path = os.path.abspath(os.path.dirname(__file__))
    print("parser_ini.py path : %s" % file_path)

    cfg_file = os.path.join(file_path,"..","pac_config","%s.ini" % str(board).strip())
    print("pac config file :", cfg_file)
    if not os.path.exists(cfg_file):
        print("Config file : %s not exit. Please check!!" % cfg_file)
        print("cp_sign_fail")
        sys.exit(1)
    create_pac_cfg(cfg_file, str(project).strip(), out_dir, carriers=carriers)
    print("====================== parser_ini end ==============================")