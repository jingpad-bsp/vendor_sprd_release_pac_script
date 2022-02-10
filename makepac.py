# -*- coding: utf-8 -*-

"""
脚本作用：
    A)指定分区img转化格式
    B)制作pac
    C)拷贝营运商信息、img、bin、xml等到out指定目录，不压缩

调用方法
    python makepac.py
"""


import os
import sys
import filecmp
import shutil
import time
import subprocess
from csv import reader
#import ConfigParser
from symbols import BMConfigDir
from bt_version import BT_VERSION
import optparse
try:
    # Python3
    from configparser import ConfigParser
except ImportError:
    # Python2
    from ConfigParser import ConfigParser

CONFIG_FILE = "pac.ini"
PAC_TAR = "archive_images"
partition = "partition"
SIMG2IMG = "out/host/linux-x86/bin/simg2img"
RENAME_IMG_LIST = []
CARRIER_LIST = []
PAC_LIST = []
NOT_PAC_LIST = []
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


def main(board_path):
    if not board_path:
        board_path = 'out/target/product'
    cmd = 'find {} -maxdepth 2 -name "*.xml"'.format(board_path)
    output = exec_cmd(cmd)
    print(output)
    target_board_file = output.strip().split('\n')
    target_board_path,target_board = os.path.split(target_board_file[0])
    print("[TARGET_BOARD]:"+str(target_board_path))

    restore_product(target_board_path)
    ##判断是否编译过ota##########
    is_check_ota = False
    native_folder = os.path.join(target_board_path, "native_backup")
    if os.path.exists(os.path.join(target_board_path,"make_ota_flag")):
        if os.path.exists(native_folder):
            print("copy backup img from native_backup")
            is_check_ota = True
            for img in os.listdir(native_folder):
                img_path = os.path.join(native_folder, img)
                if os.path.isfile(img_path) and os.path.splitext(img_path)[1] == ".img":
                    if os.path.exists(os.path.join(target_board_path, img)):
                        os.remove(os.path.join(target_board_path, img))
                    shutil.copy(img_path, target_board_path)
        else:
            print("not find native_backup folder")

    cp_sign = os.path.join(target_board_path, "cp_sign")
    if not os.path.exists(cp_sign):
        print("not find cp_sign")
        return
    carrier_product_list = []
    native_product_list = []
    product_list = os.listdir(cp_sign)
    for product in product_list:
        product_path = os.path.join(cp_sign, product)
        if os.path.isfile(product_path):
            continue
        pac_ini_path = os.path.join(product_path, "pac.ini")
        carrier = read_carrier(pac_ini_path)
        if carrier.strip():
            carrier_product_list.append(product)
        else:
            native_product_list.append(product)

    print("=============== perl mkpac start =======================")


    for product in native_product_list:
        product_path = os.path.join(cp_sign, product)
        if os.path.isdir(product_path):
            print("*******[ap product:"+product+"]*************")
            backup_product(product_path)
            get_ap_product(product_path,target_board_path,is_check_ota)
            get_pac(product_path)


    for product in carrier_product_list:
        product_path = os.path.join(cp_sign, product)
        if os.path.isdir(product_path):
            print("*******[ap product:"+product+"]*************")
            get_ap_product(product_path,target_board_path,is_check_ota)
            get_pac(product_path)

    print("pac list:[")
    if len(PAC_LIST):
        for pac in PAC_LIST:
            print(pac+" [PASS]")
    if len(NOT_PAC_LIST):
        for pac_fail in NOT_PAC_LIST:
            print(pac_fail+" [FAIL]")
    print("]")
    print("=============== perl mkpac end =========================")
    ###########copy tar#############
    restore_product(target_board_path)

    print("tart copy *img *bin etc")
    copy_tar(target_board_path)
    ###########rename spase image#######
    print("unsparse list:")
    print(RENAME_IMG_LIST)
    if len(RENAME_IMG_LIST):
        for rename_img in RENAME_IMG_LIST:
            print("rename_img:"+rename_img)
            if not os.path.exists(rename_img):
                print("not find "+rename_img)
                continue
            image_path,image_name = os.path.split(rename_img)
            new_img_name = image_name[5:]
            new_img_path = os.path.join(image_path, new_img_name)
            if os.path.exists(new_img_path):
                os.remove(new_img_path)
            os.rename(rename_img, new_img_path)
    else:
        print("not unsparse image")

    restore_product(target_board_path)

def backup_product(product_path):
    pac_ini_path = os.path.join(product_path, "pac.ini")
    product_value = get_carrier_partition(pac_ini_path)
    if not product_value.strip():
        print("not find product partition")
        return
    product_img_name = product_value.split('/')[-1]
    product_img_path_tmp ='/'.join(product_value.split('/')[:-1])
    filename_new = "MAKEPAC-" + product_img_name
    if not os.path.exists(os.path.join(product_img_path_tmp, filename_new)):
        print("=====backup_product=====:"+str(product_path))
        shutil.copy(product_value, os.path.join(product_img_path_tmp, filename_new))

def restore_product(target_board_path):
    print("rename TEMP- and MAKEPAC-")
    file_list = os.listdir(target_board_path)
    for file in file_list:
        file_path = os.path.join(target_board_path, file)
        if os.path.isfile(file_path):
            if file.startswith("MAKEPAC-"):
                print("rename MAKEPAC- file:"+file)
                new_file_name = file[8:]
                if os.path.exists(os.path.join(target_board_path, new_file_name)):
                    os.remove(os.path.join(target_board_path, new_file_name))
                os.rename(os.path.join(target_board_path, file), os.path.join(target_board_path, new_file_name))
            elif file.startswith("TEMP-"):
                print("rename TEMP- file:"+file)
                new_file_name = file[5:]
                if os.path.exists(os.path.join(target_board_path, new_file_name)):
                    os.remove(os.path.join(target_board_path, new_file_name))
                os.rename(os.path.join(target_board_path, file), os.path.join(target_board_path, new_file_name))

def copy_tar(target_board_path):
    if os.path.exists(os.path.join(target_board_path, "repac")):
        print("repac,no need create archive_images")
        return
    imges_folder = os.path.join(target_board_path, PAC_TAR)
    if os.path.exists(imges_folder):
        shutil.rmtree(imges_folder,True)
    os.mkdir(imges_folder)
    current_pwd = os.getcwd()
    os.chdir(target_board_path)
    tar_cmd = 'find .  -maxdepth 1 -name "*.img"  -o -name "*.bin" -o -name "*.xml" -o -name "installed-files.txt" -o -name "PRODUCT_SECURE_BOOT_SPRD" | awk -F "/" \'{print$2}\''
    output = os.popen(tar_cmd)
    image_list = output.read().strip().replace('\n',',').split(',')
    os.chdir(current_pwd)

    if len(image_list):
        for img in image_list:
            if not img.startswith("TEMP-"):
                img_old_path = os.path.join(target_board_path, img)
                shutil.copy(img_old_path, imges_folder)

    native_folder = os.path.join(target_board_path, "native_backup")
    if os.path.exists(native_folder):
        for img in os.listdir(native_folder):
            img_path = os.path.join(native_folder, img)
            if os.path.isfile(img_path) and os.path.splitext(img_path)[1] == ".img":
                if os.path.exists(os.path.join(imges_folder, img)):
                    os.remove(os.path.join(imges_folder, img))
                shutil.copy(img_path, imges_folder)

    print("carrier list:")
    global CARRIER_LIST
    CARRIER_LIST = list(set(CARRIER_LIST))
    print(CARRIER_LIST)
    if len(CARRIER_LIST):
        for carrier in CARRIER_LIST:
            carrier_folder = os.path.join(imges_folder, carrier)
            if os.path.exists(carrier_folder):
                shutil.rmtree(carrier_folder,True)
            os.mkdir(carrier_folder)

            carrier_path = os.path.join(target_board_path, carrier)
            carrier_folder_list = os.listdir(carrier_path)
            for carrier_file in carrier_folder_list:
                carrier_file_path = os.path.join(carrier_path, carrier_file)
                if os.path.isfile(carrier_file_path) and not carrier_file.startswith('TEMP-'):
                    shutil.copy(carrier_file_path, carrier_folder)

    #删除modem bin文件
    if os.path.exists(os.path.join(target_board_path, "make_ota_flag")):
        f = open(os.path.join(target_board_path, "make_ota_flag"), 'r')
        bin_list = f.read().strip()
        f.close()
        bin_list = bin_list.split(',')
        print(bin_list)
        for bin in bin_list:
            if os.path.exists(os.path.join(imges_folder, bin)):
                os.remove(os.path.join(imges_folder, bin))

def get_pac(product_path):
    conf = BMConfigParser()
    conf.read(os.path.join(product_path, "pac.ini"))
    pac_name = conf.get("Attr", "PAC_NAME")
    if pac_name.strip():
        pac_path = os.path.join(product_path, pac_name)
        if os.path.exists(pac_path):
            PAC_LIST.append(pac_name)
            make_bt_version(product_path)
        else:
            NOT_PAC_LIST.append(pac_name)

def get_ap_product(product_path, target_board_path, is_check_ota):
    ############查询carrier###########
    carrier = ''
    carrier_flag = os.path.join(product_path, "pac.ini")
    if os.path.exists(carrier_flag):
        carrier = read_carrier(carrier_flag)
        if carrier.strip():
            CARRIER_LIST.append(carrier)
    ############拷贝运营商img###############
    if carrier.strip():
        carrier_path = os.path.join(target_board_path, carrier)
        for img in os.listdir(carrier_path):
            img_path = os.path.join(carrier_path, img)
            if os.path.isfile(img_path) and os.path.splitext(img_path)[1] == ".img":
                if os.path.exists(os.path.join(target_board_path, img)):
                    os.remove(os.path.join(target_board_path, img))
                print("copy:"+img_path)
                shutil.copy(img_path, target_board_path)
    #######转换格式########
    pac_ini_path = os.path.join(product_path, "pac.ini")
    sparse_list = parser_pac_ini(pac_ini_path)
    if len(sparse_list):
        for img in sparse_list:
            img = '/'.join(img.split('/')[1:])
            image_path,image_name = os.path.split(img)
            ##判断之前是否已转换过
            check_sparse = os.path.join(image_path, "TEMP-"+image_name)
            if os.path.exists(check_sparse):
                print("has unsparse %s"%image_name)
            else:
                sparse_check(img, image_path, "unsparse-"+image_name)
    else:
        print("not transfer sparse img ")
    #########打pac包##################
    mkpac_pl = os.path.join(SCRIPT_PATH, "mkpac.pl")
    current_pwd = os.getcwd()
    os.chdir(product_path)
    print("current path:"+os.getcwd())
    cmd = "perl %s"%(mkpac_pl)
    exec_cmd(cmd)
    os.chdir(current_pwd)

def read_carrier(carrier_flag):
    carrier_value = ''
    conf = BMConfigParser()
    conf.read(carrier_flag)
    options_list = conf.options("Attr")
    if "carrier" not in options_list:
        print("not configured carrier")
        return carrier_value
    carrier_value = conf.get("Attr", "carrier")
    return carrier_value

def get_carrier_partition(carrier_flag):
    carrier_partition = ''
    conf = BMConfigParser()
    conf.read(carrier_flag)
    options_list = conf.options("partition")
    if "carrier_partition" not in options_list:
        print("not configured carrier_partition")
        return carrier_partition
    carrier_product = conf.get("partition", "carrier_partition")

    pac_list = conf.options("pac_list")
    if carrier_product not in pac_list:
        print("not carrier_partition in pac_list")
        return carrier_partition
    product_value = conf.get("pac_list", carrier_product)

    if not product_value.strip():
        print("find product_value in empty")
        return carrier_partition

    product_value = '/'.join(product_value.split('/')[1:])

    print("get_carrier_partition--product_value:" + str(product_value))

    return product_value


def sparse_check(installed_systeimage, product_out, upsparse_image):
    print("installed_systeimage:"+str(installed_systeimage)) #需要转换的image
    print("product_out:"+str(product_out)) #image路径
    print("SIMG2IMG:"+str(SIMG2IMG))#转换工具·
    #upsparse_image  转换后的img 名称
    system_header = os.path.join(product_out, "system_header.img")
    sparse_magic = os.path.join(product_out, "sparse_magic.img")
    cmd = "dd if=%s of=%s bs=1 skip=0 count=4"%(installed_systeimage, system_header)
    exec_cmd(cmd)
    with open(sparse_magic, 'w') as out_in:
        out_in.write("\x3a\xff\x26\xed")

    result = filecmp.cmp(system_header, sparse_magic, False)
    print("cmp result:"+str(result))
    if result:
        print("[%s]transfer sparse img to unsparse img"%installed_systeimage)
        sparse_cmd = "%s %s %s"%(SIMG2IMG, installed_systeimage, os.path.join(product_out, upsparse_image))
        exec_cmd(sparse_cmd)
    else:
        print("[%s]not transfer sparse img"%installed_systeimage)
    os.remove(sparse_magic)
    os.remove(system_header)

    #####对已转换格式的img重命名##########
    upsparse_image_path = os.path.join(product_out, upsparse_image)
    if os.path.exists(upsparse_image_path):
        image_path,image_name = os.path.split(installed_systeimage)
        new_img_name = os.path.join(image_path, "TEMP-"+image_name)
        os.rename(installed_systeimage, new_img_name)
        RENAME_IMG_LIST.append(new_img_name)
        os.rename(upsparse_image_path, installed_systeimage)
    
    
def parser_pac_ini(pac_ini_path):
    #解析ini数据
    print("pac_ini_path:"+str(pac_ini_path))
    params = []
    if not os.path.exists(pac_ini_path):
        print("not find: %s"%pac_ini_path)
        return params

    conf = BMConfigParser()
    conf.read(pac_ini_path)
    options_list = conf.options("partition")
    if "sparse" not in options_list:
        print("%s not configured sparse"%pac_ini_path)
        return params

    sparse_config = conf.get("partition", "sparse")
    sparse_list = []
    if sparse_config.strip():
        if ',' in sparse_config:
            sparse_list.extend(sparse_config.strip().split(','))
        else:
            sparse_list.append(sparse_config.strip())
    else:
        print("%s not configured sparse value"%pac_ini_path)
        return params
    
    image_list = conf.options("pac_list")
    for sp in sparse_list:
        if sp not in image_list:
            continue
        sparse_path = conf.get("pac_list", sp).strip()
        params.append(sparse_path)

    return params

def exec_cmd(cmd, use_shell=False):
    print("exec command: " + cmd)
    cmd_list = split(cmd)
    proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=use_shell)

    (output, error) = proc.communicate()
    print("command output: " + output.decode())
    # exit_code = proc.wait()
    return output.decode()

def split(s):
    for row in reader([s], delimiter=" "):
        return row

def make_bt_version(product_type):
    time_tup = time.localtime(time.time())
    format_time = '%Y-%m-%d-%a:%H:%M'
    cur_time = time.strftime(format_time, time_tup)
    bt = BT_VERSION(product_type, cur_time)
    bt.out_version()

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
    #if not options.output:
    #    print init_optparse.error('Insufficient number of arguments')
    #    sys.exit(1)
    return options
    
if __name__ == "__main__":
    options = help()
    print("=============== makepac.py start =======================")
    config = BMConfigDir(SCRIPT_PATH)
    dir = config.get_dir()
    print("dir:" + dir)
    print("SCRIPT_PATH path:"+SCRIPT_PATH)
    code_path = SCRIPT_PATH.split(dir)[0]
    os.chdir(code_path)
    print("pwd:" + os.getcwd())
    main(options.output)
    print("=============== makepac.py end =========================")