# -*- coding: utf-8 -*-

"""
解析out目录下的 pac.ini 文件,拷贝相应的modem bin到到指定目录并重命名, 编译ota

调用方法
    python makeota.py
"""

import os
import shutil
#import ConfigParser
import subprocess
import zipfile
from symbols import Symbols
from symbols import BMConfigDir
import optparse
try:
    # Python3
    from configparser import ConfigParser
except ImportError:
    # Python2
    from ConfigParser import ConfigParser

CONFIG_FILE = "pac.ini"
PRODUCT_LIST = [] ##非运营商工程列表
CARRIER_PRODUCT_LIST = [] ##运营商工程列表
OTA_LIST = []
FILE_LIST = []
OLD_MODEM_IMG = []
ALL_MODEM_LIST = []
ARCHIVE_OTA = "archive_ota"
ARCHIVE_OTA_OLD = "archive_ota_old"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
NATIVE_PRODUCT=''
NATIVE_PRODUCT_GSI=''

def main(target_board_path):
    global ALL_MODEM_LIST
    global NATIVE_PRODUCT
    global NATIVE_PRODUCT_GSI

    if os.path.exists(os.path.join(target_board_path,"make_ota_flag")):
        os.remove(os.path.join(target_board_path,"make_ota_flag"))

    cp_sign = os.path.join(target_board_path, "cp_sign")
    if not os.path.exists(cp_sign):
        print("not find %s" % str(cp_sign))
        return
    carrier_list = []
    ap_list = os.listdir(cp_sign)
    for product in ap_list:
        product_path = os.path.join(cp_sign, product)
        if os.path.isfile(product_path):
            continue
        pac_ini_path = os.path.join(product_path, "pac.ini")
        ota_flag = read_ota_flag(pac_ini_path)
        if ota_flag[0] =="true":
            if ota_flag[1].strip():
                CARRIER_PRODUCT_LIST.append(product)
            else:
                PRODUCT_LIST.append(product)
        else:
            if not ota_flag[1].strip():
                if "GSI" in product or "gsi" in product:
                    NATIVE_PRODUCT_GSI = product
                else:
                    NATIVE_PRODUCT = product
        if ota_flag[1].strip():
            carrier_list.append(ota_flag[1].strip())

    carrier_list = list(set(carrier_list))
    print("carrier:")
    print(carrier_list)
    remove_zip(carrier_list,target_board_path)
    for file in carrier_list:
        file_path = os.path.join(target_board_path, file)
        if not os.path.exists(file_path):
            continue
        carrier_filag = os.path.join(target_board_path, file, "ota_flag")
        if os.path.exists(carrier_filag):
            f = open(carrier_filag, 'r')
            base_target_file = f.read().strip()
            f.close()
            print("base_target_file:" + base_target_file)
            if os.path.exists(os.path.join(target_board_path, file, base_target_file)):
                os.remove(os.path.join(target_board_path, file, base_target_file))
            os.remove(carrier_filag)

    print("native ota list:")
    print(PRODUCT_LIST)
    print("carrier ota list:")
    print(CARRIER_PRODUCT_LIST)
    if not len(PRODUCT_LIST) and not len(CARRIER_PRODUCT_LIST):
        print("no need to make ota")
        return
    archive_ota = os.path.join(target_board_path, ARCHIVE_OTA)
    if os.path.exists(archive_ota):
        shutil.rmtree(archive_ota, True)
    os.mkdir(archive_ota)
    #先编译非运营商的ota,再编译运营商ota
    is_check_native = False
    if len(PRODUCT_LIST):
        is_check_native = True
        make_native_ota(target_board_path, cp_sign, archive_ota)
    if len(CARRIER_PRODUCT_LIST):
        make_carrier_ota(is_check_native,target_board_path, cp_sign, archive_ota)
    print("ota list[")
    print(OTA_LIST)
    print("]")
    print("target-files list:[")
    print(FILE_LIST)
    print("]")

    ALL_MODEM_LIST = list(set(ALL_MODEM_LIST))
    print("ALL_MODEM_LIST:")
    print(ALL_MODEM_LIST)
    f2 = open(os.path.join(target_board_path,"make_ota_flag"), 'a')
    f2.write(','.join(ALL_MODEM_LIST))
    f2.close()
    remove_zip(carrier_list, target_board_path)

def remove_zip(carrier_list, target_board_path):
    for file in carrier_list:
        file_path = os.path.join(target_board_path, file)
        if not os.path.exists(file_path):
            continue
        carrier_filag = os.path.join(target_board_path, file, "ota_flag")
        if os.path.exists(carrier_filag):
            f = open(carrier_filag, 'r')
            base_target_file = f.read().strip()
            f.close()
            print("base_target_file:" + base_target_file)
            if os.path.exists(os.path.join(target_board_path, file, base_target_file)):
                os.remove(os.path.join(target_board_path, file, base_target_file))
            os.remove(carrier_filag)

def make_carrier_ota(is_check_native,target_board_path, cp_sign, archive_ota):
    """
    编译运营商ota
    """
    print("is_check_native:"+str(is_check_native))
    if not is_check_native:
        print("***********backup native***********")
        # 备份img和symbols
        symbols_folder = os.path.join(target_board_path, "native_backup")
        if os.path.exists(symbols_folder):
            shutil.rmtree(symbols_folder)
        os.mkdir(symbols_folder)
        backup_img(target_board_path, symbols_folder, "")

    for product in CARRIER_PRODUCT_LIST:
        print("*******[ap product:" + product + "]*************")
        product_path = os.path.join(cp_sign, product)
        product_carrier = product.split('_')[-1]
        carrier_filag = os.path.join(target_board_path, product_carrier, "ota_flag")
        if os.path.exists(carrier_filag):
            f = open(carrier_filag, 'r')
            base_target_file = f.read().strip()
            f.close()
            print("base_target_file:"+base_target_file)
            if base_target_file.strip():
                update_ota(target_board_path, cp_sign, product, base_target_file)
            else:
                make_ota(archive_ota, product_path, target_board_path, product)
        else:
            make_ota(archive_ota, product_path, target_board_path, product)

def make_native_ota(target_board_path, cp_sign, archive_ota):
    """
    编译非运营商ota
    """
    native_backup = os.path.join(target_board_path, "native_backup")  # 用来保存第一个非运营商的img和symbols
    if os.path.exists(native_backup):
        shutil.rmtree(native_backup)
    os.mkdir(native_backup)
    product = PRODUCT_LIST[0]  # 取其中第一个工程编译，后面的非运营商直接update modem
    del PRODUCT_LIST[0]
    print("*******[ap product:" + product + "]*************")
    product_path = os.path.join(cp_sign, product)
    make_ota(archive_ota,product_path, target_board_path, product)
    #备份img和symbols
    symbols_folder = os.path.join(target_board_path, "native_backup")
    if os.path.exists(symbols_folder):
        shutil.rmtree(symbols_folder)
    os.mkdir(symbols_folder)
    backup_img(target_board_path,symbols_folder,product)
    print("update product:")
    print(PRODUCT_LIST)
    if not len(PRODUCT_LIST):
        return
    base_target_file = ''
    target_files_list = os.listdir(archive_ota)
    for file in target_files_list:
        if "-target_files-" in file and os.path.splitext(file)[1] == ".zip":
            base_target_file = file
    if not base_target_file.strip():
        print("not find base target-files")
        return

    for update_product in PRODUCT_LIST:
        print("*******[ap product:" + update_product + "]*************")
        print("FILE_LIST:")
        print(FILE_LIST)
        update_ota(target_board_path, cp_sign, update_product, base_target_file)


def backup_img(target_board_path, symbols_folder, product):
    """
    备份vendor、system、product和 symbols
    """
    sysbol = Symbols(target_board_path, symbols_folder)
    sysbol.copy_symbols()
    if not product.strip():
        print("NATIVE_PRODUCT:" + NATIVE_PRODUCT)
        if NATIVE_PRODUCT.strip():
            product = NATIVE_PRODUCT
        elif NATIVE_PRODUCT_GSI.strip():
            product = NATIVE_PRODUCT_GSI

    pac_ini_path = os.path.join(target_board_path, "cp_sign", product, "pac.ini")
    if not os.path.exists(pac_ini_path):
        print("not find pac_ini_path:"+str(pac_ini_path))
        return
    print("pac_ini_path:" + str(pac_ini_path))
    backup_img_list = get_backup_partition(pac_ini_path)
    print("backup_img_list:")
    print(backup_img_list)
    if not len(backup_img_list):
        print("backup_img_list is empty. ")
        return
    for item in backup_img_list:
        print("backup img:"+item)
        if "out/" in item:
            product_img_name = item.split('/')[-1]
            if os.path.exists(os.path.join(symbols_folder, product_img_name)):
                continue
            shutil.copy(item, symbols_folder)

def update_ota(target_board_path, cp_sign, product, base_target):
    archive_ota_path = os.path.join(target_board_path,ARCHIVE_OTA)
    files_folder = os.path.join(archive_ota_path, "OTA_FILE")
    if os.path.exists(files_folder):
        shutil.rmtree(files_folder)
    os.mkdir(files_folder)
    print("unzip base target-files")
    z = zipfile.ZipFile(os.path.join(archive_ota_path,base_target), 'r')
    z.extractall(path=files_folder)
    z.close()
    print("OLD_MODEM_IMG:")
    print(OLD_MODEM_IMG)
    if len(OLD_MODEM_IMG):
        for old_bin in OLD_MODEM_IMG:
            files_path = os.path.join(files_folder, "RADIO",old_bin)
            if os.path.exists(files_path):
                os.remove(files_path)
    cp_modem(os.path.join(cp_sign,product),files_folder,product,archive_ota_path)

    if os.path.exists(files_folder):
        shutil.rmtree(files_folder)

def cp_modem(product_path, files_folder, product, base_ota_path):
    ####更新base ota里面的bin文件#######
    modem_dict = {}
    pac_ini_path = os.path.join(product_path, "pac.ini")
    print("pac_ini_path:"+str(pac_ini_path))
    conf = BMConfigParser()
    conf.read(pac_ini_path)
    pac_name = conf.get("Attr", "PAC_NAME").strip()
    ota_partition = conf.get("partition", "ota_partition")
    print("******ota_partition*******")
    print(ota_partition)
    dest_ota_modem = ota_partition.strip().replace('\n',',').split(',')
    print(dest_ota_modem)
    for modem in dest_ota_modem:
        modem_key = modem.split(':')[0]
        modem_value = modem.split(':')[1]
        if modem_value.strip():
            modem_path,modem_name = os.path.split(modem_value)
            modem_dict[modem_key] = modem_name
            ALL_MODEM_LIST.append(modem_name)

    for key,values in modem_dict.items():
        souce_m_value = conf.get("pac_list", key)
        souce_m_value = '/'.join(souce_m_value.split('/')[1:])
        print(souce_m_value)
        if souce_m_value.strip() and values.strip():
            update_img(files_folder, souce_m_value, values)

    pac_name_split = pac_name.split('-')
    project_name = pac_name_split[0]
    project_ver = pac_name_split[1]
    print("project_name:"+project_name+",project_ver:"+project_ver)
    print("=====zip target-files=====")
    current_path = os.getcwd()
    os.chdir(files_folder)
    print("current path:"+os.getcwd())
    new_target_files_name = project_name + "-target_files-" + product + ".zip"
    cmd = "zip  -r  %s  *"%new_target_files_name
    os.system(cmd)
    print("=====zip target-files end=====")
    os.chdir(current_path)
    new_ota = os.path.join(files_folder, new_target_files_name)
    if not os.path.exists(new_ota):
        print("=====update ota fail !!=====")
        return
    shutil.copy(new_ota, base_ota_path)
    print("=====zip ota=====")
    zip_target_files_name = os.path.join(base_ota_path, project_name + "-target_files-" + product + ".zip")
    zip_ota_name = os.path.join(base_ota_path, project_name+"-ota-"+product+".zip")
    cmd = 'build/tools/releasetools/ota_from_target_files.py --block %s %s'%(zip_target_files_name, zip_ota_name)
    p = subprocess.Popen(cmd, shell=True, executable="/bin/bash")
    os.waitpid(p.pid, 0)
    OTA_LIST.append(project_name+"-ota-"+product+".zip")
    FILE_LIST.append(project_name+"-target_files-"+product+".zip")

def update_img(files_folder, souce_m_value, new_name):
    souce_m_path,souce_m_name = os.path.split(souce_m_value)

    update_files_img = os.path.join(files_folder, "RADIO",new_name)
    radio_path = os.path.join(files_folder, "RADIO")
    print("update target files:"+new_name)
    shutil.copy(souce_m_value, radio_path)
    os.rename(os.path.join(radio_path, souce_m_name), update_files_img)


def make_ota(archive_ota, product_path, target_board_path, product):
    modem_dict = {}
    pac_ini_path = os.path.join(product_path, "pac.ini")
    print("pac_ini_path:"+str(pac_ini_path))
    conf = BMConfigParser()
    conf.read(pac_ini_path)
    ota_partition = conf.get("partition", "ota_partition")
    print("******ota_partition*******")
    print(ota_partition)
    dest_ota_modem = ota_partition.strip().replace('\n',',').split(',')
    print(dest_ota_modem)
    for modem in dest_ota_modem:
        modem_key = modem.split(':')[0]
        modem_value = modem.split(':')[1]
        if modem_value.strip():
            modem_value = '/'.join(modem_value.split('/')[1:])
            modem_dict[modem_key] = modem_value
            modem_path, modem_name = os.path.split(modem_value)
            OLD_MODEM_IMG.append(modem_name)
            ALL_MODEM_LIST.append(modem_name)

    for key,values in modem_dict.items():
        souce_m_value = conf.get("pac_list", key)
        souce_m_value = '/'.join(souce_m_value.split('/')[1:])
        print(souce_m_value)
        if souce_m_value.strip() and values.strip():
            copy_img(souce_m_value, values)
    pac_name = conf.get("Attr", "PAC_NAME").strip()
    carrier_name = conf.get("Attr", "carrier").strip()
    print("pac name:"+pac_name)
    build(archive_ota, pac_name,carrier_name,target_board_path, product)
    if carrier_name.strip():
        # 备份img和symbols
        symbols_folder = os.path.join(target_board_path, carrier_name)
        backup_img(target_board_path, symbols_folder, product)

def build(archive_ota, pac_name, carrier_name, target_board_path, product):
    print("carrier="+carrier_name)
    carrier_product = ''
    if carrier_name.strip():
        for file in os.listdir(os.path.join(target_board_path, carrier_name)):
            carrier_file = os.path.join(target_board_path, carrier_name, file)
            if os.path.isfile(carrier_file) and os.path.splitext(file)[1] == '.img':
                os.remove(os.path.join(target_board_path, file))
                shutil.copy(carrier_file, target_board_path)
                carrier_product = file

    pac_name_split = pac_name.split('-')
    project_name = pac_name_split[0]
    project_ver = pac_name_split[1]
    project_vlx = pac_name_split[2].split('_')[0]

    print("project_name=%s, project_ver=%s, project_vlx=%s"%(project_name, project_ver, project_vlx))
    cmd = 'grep "ro.build.version.sdk=" %s/system/build.prop | awk -F "=" \'{print $NF}\''%target_board_path
    print(cmd)
    output = os.popen(cmd)
    platform_version = output.read().strip().replace("\n",",").split(',')[0]

    print("platform_version:"+platform_version)
    cmd = 'cat /proc/cpuinfo | grep -i \'processor\' | wc -l'
    output = os.popen(cmd)
    cpu_count = output.read().strip().replace("\n",",").split(',')[0]
    print("cpu count:"+cpu_count)
    if int(platform_version) >=28:
        cmd = 'source build/envsetup.sh\nchoosecombo 1 %s %s %s\nmake otapackage -j%s'%(project_name, project_ver, project_vlx, cpu_count)
        p = subprocess.Popen(cmd, shell=True, executable="/bin/bash")
        os.waitpid(p.pid, 0)
    else:
        cmd = 'source build/envsetup.sh\nchoosecombo 1 %s %s\nmake otapackage -j%s'%(project_name, project_ver, cpu_count)
        p = subprocess.Popen(cmd, shell=True, executable="/bin/bash")
        os.waitpid(p.pid, 0)
    ##########对ota进行重命名##########
    otazip = project_name+"-ota-"

    for filename in os.listdir(target_board_path):
        print("filename:"+filename)
        if otazip in filename and os.path.splitext(filename)[1] == '.zip':
            otazip_path = os.path.join(target_board_path, filename)
            shutil.move(otazip_path, archive_ota)
            new_ota_name = os.path.join(archive_ota, project_name+"-ota-"+product+".zip")
            os.rename(os.path.join(archive_ota, filename), new_ota_name)
            OTA_LIST.append(project_name+"-ota-"+product+".zip")
            print("copy ota success")

    target_files_path = os.path.join(target_board_path, "obj/PACKAGING/target_files_intermediates")
    if not os.path.exists(target_files_path):
        print("==========make ota fail!!===========")
        return
    target_files_zip = project_name+"-target_files-"
    for filename in os.listdir(target_files_path):
        if target_files_zip in filename and os.path.splitext(filename)[1] == '.zip':
            target_files = os.path.join(target_files_path, filename)
            new_target_files_name = os.path.join(target_files_path, project_name + "-target_files-" + product + ".zip")
            os.rename(target_files, new_target_files_name)
            if carrier_name.strip():
                if os.path.exists(os.path.join(target_board_path, carrier_name, "ota_flag")):
                    os.remove(os.path.join(target_board_path, carrier_name, "ota_flag"))
                f = open(os.path.join(target_board_path, carrier_name, "ota_flag"), 'a')
                f.write(project_name + "-target_files-" + product + ".zip")
                f.close()
            shutil.move(new_target_files_name, archive_ota)
            FILE_LIST.append(project_name+"-target_files-"+product+".zip")
            print("copy target_files success")

    if carrier_product.strip():
        carrier_file_new = os.path.join(target_board_path, carrier_name, carrier_product)
        os.remove(carrier_file_new)
        shutil.copy(os.path.join(target_board_path, carrier_product), carrier_file_new)

def copy_img(souce_m_value, dest_m_value):
    print("souce_m_value:"+souce_m_value)
    print("dest_m_value:"+dest_m_value)
    if os.path.exists(souce_m_value):
        if os.path.isfile(souce_m_value):
            dest_m_path,dest_m_name = os.path.split(dest_m_value)
            if not os.path.exists(dest_m_path):
                os.mkdir(dest_m_path)
            souce_m_path,souce_m_name = os.path.split(souce_m_value)
            shutil.copy(souce_m_value, dest_m_path)
            os.rename(os.path.join(dest_m_path, souce_m_name), dest_m_value)

def read_ota_flag(pac_ini_path):
    print("pac_ini_path:"+str(pac_ini_path))
    if not os.path.exists(pac_ini_path):
        print("not find: %s"%pac_ini_path)
        return ['','']
    conf = BMConfigParser()
    conf.read(pac_ini_path)
    options_list = conf.options("Attr")
    if "ota_flag" not in options_list:
        print("pac.ini not configured sparse")
        return ['','']
    ota_flag = conf.get("Attr", "ota_flag")
    carrier_flag = conf.get("Attr", "carrier")
    return [ota_flag, carrier_flag]

def get_backup_partition(pac_ini_path):
    print("pac_ini_path:" + str(pac_ini_path))
    ota_backup_list = []
    if not os.path.exists(pac_ini_path):
        print("not find: %s" % pac_ini_path)
        return ota_backup_list
    conf = BMConfigParser()
    conf.read(pac_ini_path)
    options_list = conf.options("partition")
    if "ota_build_backup" not in options_list:
        print("pac.ini not ota_build_backup")
        return ota_backup_list
    ota_backup_par = conf.get("partition", "ota_build_backup").strip()
    print("ota_backup_par:")
    print(ota_backup_par)
    ota_backup_list=[]
    pat_list=[]
    if ',' in ota_backup_par:
        pat_list = ota_backup_par.split(",")
    else:
        pat_list.append(ota_backup_par)
    print("pat_list:")
    print(pat_list)
    for item in pat_list:
        if not item.strip():
            continue
        item_par = conf.get("pac_list", item).strip()
        if "/" in item_par:
            item_par = '/'.join(item_par.split("/")[1:])
            ota_backup_list.append(item_par)
    return ota_backup_list


def repac_ota(target_board_path):
    print("=============== repac make ota start =======================")
    archive_ota_old = os.path.join(target_board_path, ARCHIVE_OTA_OLD)
    if not os.path.exists(archive_ota_old):
        print("****not find archive_ota_old folder****")
        return
    cp_sign = os.path.join(target_board_path, "cp_sign")
    if not os.path.exists(cp_sign):
        print("****not find cp_sign folder****")
        return
    archive_ota = os.path.join(target_board_path, ARCHIVE_OTA)
    if os.path.exists(archive_ota):
        shutil.rmtree(archive_ota, True)
    os.mkdir(archive_ota)
    files_folder = os.path.join(archive_ota, "OTA_FILE")
    for file in os.listdir(archive_ota_old):
        if "-target_files-" not in file:
            print("bad file:" + file)
            continue
        print("base target file:"+file)
        base_target_files = os.path.join(archive_ota_old, file)
        product = file.split('.')[0].split('-')[-1]
        shutil.copy(base_target_files, archive_ota)
        os.rename(os.path.join(archive_ota,file), os.path.join(archive_ota,"BASE_"+file))
        update_ota(target_board_path, cp_sign, product, "BASE_"+file)
        os.remove(os.path.join(archive_ota,"BASE_"+file))

    print("ota list[")
    print(OTA_LIST)
    print("]")
    print("target-files list:[")
    print(FILE_LIST)
    print("]")

    if os.path.exists(files_folder):
        shutil.rmtree(files_folder)

    print("=============== repac make ota end =======================")

class BMConfigParser(ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, option_str):
        return option_str


def help():
    init_optparse = optparse.OptionParser(
        usage="usage: %prog [options] args", description="show help"
    )
    init_optparse.add_option(
        '-o', '--out', help='output path', dest='output', type="string")

    (options, args) = init_optparse.parse_args()
    # if not options.output:
    #    print init_optparse.error('Insufficient number of arguments')
    #    sys.exit(1)
    return options

if __name__ == "__main__":
    options = help()
    board_path = options.output
    print("=============== make ota start =======================")
    config = BMConfigDir(SCRIPT_PATH)
    dir = config.get_dir()
    print("dir:" + dir)
    code_path = SCRIPT_PATH.split(dir)[0]
    os.chdir(code_path)
    print("pwd:" + os.getcwd())
    if not board_path:
        board_path = 'out/target/product'
    cmd = 'find {} -maxdepth 2 -name "*.xml"'.format(board_path)
    output = os.popen(cmd)
    target_board_file = output.read().strip().replace("\n", ",").split(',')
    target_board_path, target_board = os.path.split(target_board_file[0])
    print("TARGET_BOARD:" + str(target_board_path))
    if os.path.exists(os.path.join(target_board_path, "repac")):
        repac_ota(target_board_path)
    else:
        main(target_board_path)
    print("=============== make ota end =======================")
