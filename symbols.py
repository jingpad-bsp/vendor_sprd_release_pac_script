# -*- coding: utf-8 -*-

"""
解析当前目录下的 config.ini 文件
    A)拷贝ini文件中[symbols]里vmlinux、vendor、system 等对应的路径下的文件到out/symbols/(symbols.vmlinux、symbols.vendor、symbols.system
    B)ini路径中带'>'表示重命

调用方法
    python sysbols.py
"""

import sys
import os
import shutil
#import ConfigParser

try:
    # Python3
    from configparser import ConfigParser
except ImportError:
    # Python2
    from ConfigParser import ConfigParser

CONFIG_FILE = "config.ini"
PAC_CONFIG_BRANCH = "pac_config"
SYMBOLS = "symbols"
NOT_FIND_LIST = []
FIND_LIST = []
CARRIER_LIST = []
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

class Symbols(object):
    
    def __init__(self, target_board_path, symbols_folder):
        self.target_board_path = target_board_path
        self.symbols_folder = symbols_folder

    def copy_symbols(self):
        symbols_folder = self.symbols_folder
        target_board_path = self.target_board_path
        parameters = self.configParser()
        for key in parameters.keys():
            value = parameters.get(key).strip().replace("\n",",").split(',')
            self.copy_options(key,value,target_board_path,symbols_folder)

        ################归类log####################
        for key in parameters.keys():
            smbols_flag_key = SYMBOLS+"."+key
            print("[%s]"%smbols_flag_key)
            smbols_flag_list = []
            for item1 in FIND_LIST:
                if "@@" in item1:
                    symbols_key = item1.split('@@')[0].strip()
                    symbols_value = item1.split('@@')[1].strip()
                    if symbols_key == smbols_flag_key:
                        print("find %s"%str(symbols_value))
            for item2 in NOT_FIND_LIST:
                if "@@" in item2:
                    symbols_key = item2.split('@@')[0].strip()
                    symbols_value = item2.split('@@')[1].strip()
                    if symbols_key == smbols_flag_key:
                        print("not find %s"%str(symbols_value))

    def copy_options(self, key, value, target_board_path, symbols_folder):
        for item in value:
            self.copy_parame(item, SYMBOLS+"."+key, target_board_path, symbols_folder)

    def copy_parame(self, symbols_file, new_folder_name, target_board_path, symbols_folder):
        symbols_file_tmp = symbols_file
        print(new_folder_name,": ",symbols_file_tmp)
        if '>' in symbols_file:
            symbols_file = symbols_file_tmp.split('>')[0].strip()
            symbols_file_path,symbols_old_name = os.path.split(symbols_file)
            symbols_new_name = symbols_file_tmp.split('>')[1].strip()

        else:
            symbols_file_path,symbols_old_name = os.path.split(symbols_file)
            symbols_new_name = symbols_old_name

        board = target_board_path.split('/')[-1]
        symbols_path = symbols_file.replace('$BOARD',board)
        if '.' in symbols_path:
            symbols_path = symbols_path.split('./')[-1]
        symbols_full_file = symbols_path

        if os.path.exists(symbols_full_file):
            FIND_LIST.append(new_folder_name+"@@"+symbols_file)
            dest_symbols_path = os.path.join(symbols_folder, new_folder_name)
            if not os.path.exists(dest_symbols_path):
                os.mkdir(dest_symbols_path)

            if os.path.isfile(symbols_full_file):
                shutil.copy(symbols_full_file, dest_symbols_path)
                old_file_name = os.path.join(dest_symbols_path, symbols_old_name)
                new_file_name = os.path.join(dest_symbols_path, symbols_new_name)
                os.rename(old_file_name,new_file_name)
            else:
                if '>' in symbols_file_tmp:
                    dest_symbols_path = os.path.join(dest_symbols_path, symbols_new_name)
                    os.makedirs(os.path.join(dest_symbols_path))

                if os.path.exists(dest_symbols_path):
                    shutil.rmtree(dest_symbols_path,True)
                shutil.copytree(symbols_full_file, dest_symbols_path,symlinks=True)
        else:
            NOT_FIND_LIST.append(new_folder_name+"@@"+symbols_file)

    def copy_symbols_for_ota(self):
        print("======copy_symbols_for_ota===========")
        native_folder = os.path.join(target_board_path, "native_backup")
        if os.path.exists(native_folder):
            for folder in os.listdir(native_folder):
                print("folder:"+folder)
                folder_path = os.path.join(native_folder, folder)
                if os.path.isdir(folder_path) and "symbols" in folder:
                    self.copy_dir(folder, folder_path, self.symbols_folder)
        else:
            print("not find native_backup folder")

        cp_sign = os.path.join(target_board_path, "cp_sign")
        if not os.path.exists(cp_sign):
            print("not find %s" % str(cp_sign))
            return
        ap_list = os.listdir(cp_sign)
        for product in ap_list:
            product_path = os.path.join(cp_sign, product)
            if os.path.isfile(product_path):
                continue
            pac_ini_path = os.path.join(product_path, "pac.ini")
            ota_flag = self.read_ota_flag(pac_ini_path)
            if ota_flag[0] == "true":
                carrier = ota_flag[1]
                if carrier.strip():
                    CARRIER_LIST.append(carrier)
        print(CARRIER_LIST)
        for symbols in os.listdir(self.symbols_folder):
            for carrier in CARRIER_LIST:
                carrier_path = os.path.join(target_board_path, carrier)
                for folder in os.listdir(carrier_path):
                    folder_path = os.path.join(carrier_path, folder)
                    if os.path.isdir(folder_path) and folder == symbols:
                        carrier_folder = os.path.join(self.symbols_folder, symbols, carrier)
                        print(carrier_folder)
                        if os.path.exists(carrier_folder):
                            shutil.rmtree(carrier_folder, True)
                        shutil.copytree(folder_path, carrier_folder, symlinks=True)

        print("make ota carrier list:")
        print(CARRIER_LIST)

    def copy_dir(self, folder_name, dir, out):
        out_folder = os.path.join(out, folder_name)
        print("out_folder:"+out_folder)
        if os.path.exists(out_folder):
            shutil.rmtree(out_folder, True)
        shutil.copytree(dir, out_folder, symlinks=True)

    def configParser(self):
        #解析ini数据
        config=os.path.abspath(os.path.join(SCRIPT_PATH,"..", PAC_CONFIG_BRANCH, CONFIG_FILE))
        if not os.path.exists(config):
            print("not find config.ini")
            sys.exit(1)

        conf = BMConfigParser()
        conf.read(config)
    
        options_list = conf.options(SYMBOLS)
        print(options_list)
        options_dict = {}
    
        for option in options_list:
            param = conf.get(SYMBOLS, option)
            options_dict[option] = param

        return options_dict

    def read_ota_flag(self, pac_ini_path):
        print("pac_ini_path:" + str(pac_ini_path))
        if not os.path.exists(pac_ini_path):
            print("not find: %s" % pac_ini_path)
            return ['', '']
        conf = BMConfigParser()
        conf.read(pac_ini_path)
        options_list = conf.options("Attr")
        if "ota_flag" not in options_list:
            print("pac.ini not configured sparse")
            return ['', '']
        ota_flag = conf.get("Attr", "ota_flag")
        carrier_flag = conf.get("Attr", "carrier")
        return [ota_flag, carrier_flag]

class BMConfigParser(ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, option_str):
        return option_str

class BMConfigDir(object):
    def __init__(self, sctipt_path):
        self.sctipt_path = sctipt_path

    def get_dir(self):
        config = os.path.abspath(os.path.join(self.sctipt_path, "..", PAC_CONFIG_BRANCH, CONFIG_FILE))
        if not os.path.exists(config):
            print("not find config.ini")
            sys.exit(1)

        conf = BMConfigParser()
        conf.read(config)
        dir = conf.get("work_dir", "dir")
        return dir

if __name__ == "__main__":
    print("=============== copy symbols start =======================")
    config = BMConfigDir(SCRIPT_PATH)
    dir = config.get_dir()
    print("dir:" + dir)
    code_path = SCRIPT_PATH.split(dir)[0]
    os.chdir(code_path)
    print("pwd:"+os.getcwd())

    cmd = 'find out/target/product -maxdepth 2 -name "*.xml"'
    output = os.popen(cmd)
    target_board_file = output.read().strip().replace("\n",",").split(',')
    target_board_path,target_board = os.path.split(target_board_file[0])
    print("TARGET_BOARD:"+str(target_board_path))
    if os.path.exists(os.path.join(target_board_path, "repac")):
        print("repac,no need create archive_symbols")
    else:
        symbols_folder = os.path.join(target_board_path, "archive_symbols")
        if os.path.exists(symbols_folder):
            shutil.rmtree(symbols_folder, True)
        os.mkdir(symbols_folder)
        symbols = Symbols(target_board_path,symbols_folder)
        if os.path.exists(os.path.join(target_board_path, "make_ota_flag")):
            symbols.copy_symbols_for_ota()
        else:
            symbols.copy_symbols()
    print("=============== copy symbols end =======================")