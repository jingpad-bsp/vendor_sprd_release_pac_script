# -*- coding: utf-8 -*-

"""
解析当前目录下的 common.ini 文件,获取cp0/cp2/gnss等信息生成version.txt文件

调用方法
    python bt_version.py
"""

import os
import time
#import ConfigParser
#from symbols import BMConfigDir
try:
    # Python3
    from configparser import ConfigParser
except ImportError:
    # Python2
    from ConfigParser import ConfigParser

CONFIG_FILE = "common.ini"
VERSION_TXT = "bt_version.txt"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

class BT_VERSION(object):
    def __init__(self, product, pac_time):
        self.product = product
        self.pac_time = pac_time
        common_ini = self.parse_common_ini()
        self.cp0_version = common_ini[0].strip()
        self.cp2_version = common_ini[1].strip()
        self.gnss_version = common_ini[2].strip()
        self.cp2_version_txt = ''
        self.gnss_version_txt = ''
        self.pac_name = ''

    def get_pac_name(self):
        print("====get_pac_name=====")
        conf = BMConfigParser()
        conf.read(os.path.join(self.product, "pac.ini"))
        pac_name = conf.get("Attr", "PAC_NAME")
        self.pac_name = pac_name.split('.')[0]
        print("pac_name:"+self.pac_name)
        return self.pac_name

    def get_pac_time(self):
        print("====get_pac_time=====")
        print("pac_time:"+str(self.pac_time))
        return self.pac_time

    def get_ap(self):
        print("====get_ap=====")
        board_path = self.product.split('cp_sign')[0]
        system_build_path = os.path.join(board_path,"system","build.prop")
        if not os.path.exists(system_build_path):
            cmd1 = 'find %s  -maxdepth 1 -name "*.json"'%board_path
            json_path_tmp = os.popen(cmd1).read().strip()
            if not os.path.exists(json_path_tmp):
                print("not find json file")
                return ""
            json_path,json_name = os.path.split(json_path_tmp)
            current_cwd = os.getcwd()
            os.chdir(board_path)
            cmd2 = 'grep -ri \'"DISTRO_VERSION":\'  %s'%json_name
            ap = os.popen(cmd2).read().strip()
            if not ap.strip():
                print("****not find DISTRO_VERSION****")
                return ""
            ap = ap.split('"')[3]
            print("ap:" + ap)
            os.chdir(current_cwd)
            return ap
        else:
            cmd2 = "grep ro.build.description %s"%system_build_path
            ap = os.popen(cmd2).read().strip()
            if not ap.strip():
                print("*****not find ro.build.description*****")
                return ''
            ap = ap.split('=')[-1]
            print(ap)
        return ap


    def get_cp0(self):
        print("====get_cp0====")
        cp0_version_options = self.cp0_version.split('\n')
        print(cp0_version_options)
        modem_value = ''
        for modem_key in cp0_version_options:
            value = self.get_modem_bin(modem_key)
            modem_value = value.strip().strip('1@')
            if not modem_value:
                continue
            break
      
        if not modem_value:
            print('*****modem_value is null*****')
            return ''
        img = modem_value.strip('./')
        cmd = 'strings %s | grep  "HW Version:" | awk \'{print $NF}\'' %(img)
        hw_version = os.popen(cmd).read().strip()
        cmd2 = 'strings %s | grep  "BASE  Version:" | awk \'{print $NF}\'' % (img)
        base_version = os.popen(cmd2).read().strip()
        cmd3 = 'strings %s | grep -Po "\d{2}-\d{2}-\d{4} \d{1,2}:\d{1,2}:\d{1,2}"' % (img)
        kernel_time = os.popen(cmd3).read().strip()
        cp0_version = '|'.join([base_version, hw_version, kernel_time])
        print("CP0_Version:"+cp0_version)
        return cp0_version



    def get_cp2(self):
        print('=====get_cp2=====')
        cp2_version_options = self.cp2_version.split('\n')
        print(cp2_version_options)
        modem_value = ''
        for modem_key in cp2_version_options:
            value = self.get_modem_bin(modem_key)
            modem_value = value.strip()
            modem_value = modem_value.strip('1@')
            if not modem_value:
                continue
            break
           
        if not modem_value:
            print('*****modem_value is null*****')
            return ''
        img = modem_value.strip('./')
        tmp_path = os.path.dirname(img)
        for i in range(10):
            if not tmp_path:
                print("*****not found cp2 version txt*****")
                return ""
            version_path = os.path.join(tmp_path, 'version.txt')
            print("[CHECK]version path:" + version_path)
            if os.path.isfile(version_path):
                with open(version_path,'r') as f:
                    cp2_version = f.read()
                print("version_txt: {} \ncp2_version:{}".format(version_path, cp2_version))
                return cp2_version.strip()          
            tmp_path = os.path.dirname(tmp_path)            

    def get_firmware(self):
        print("======get_firmware======")
        versioninfo_path = "vendor/sprd/modules/gpsfirmware/versioninfo.txt"
        if not os.path.exists(versioninfo_path):
            print("*****not found gpsfirmware*****")
            return ''

        cmd = "grep 'GE2:' %s" % versioninfo_path
        firmware = os.popen(cmd).read().strip()
        if not firmware:
            print("*****firmware is null*****")
            return ''
        firmware = firmware.split('@')[-1]
        print(firmware)
        return firmware


    def get_gnss_version(self):
        print("======get_gnss_version======")
        gnss_version_options = self.gnss_version.split('\n')
        print(gnss_version_options)
        modem_value = ''
        for modem_key in gnss_version_options:
            value = self.get_modem_bin(modem_key)
            modem_value = value.strip()
            modem_value = modem_value.strip('1@')
            if not modem_value:
                continue
            break
        if not modem_value:
            print('*****modem_value is null*****')
            return ''
            
        img = modem_value.strip('./')
        tmp_path = os.path.dirname(img)
        for i in range(10):
            if not tmp_path:
                print("*****not found gnss version txt*****")
                return ""
            version_path = os.path.join(tmp_path, 'version.txt')
            print("[CHECK]version path:" + version_path)
            if os.path.isfile(version_path):
                with open(version_path,'r') as f:
                    gnss_version = f.read()
                print("version_txt: {} \ngnss_version:{}".format(version_path, gnss_version))
                return gnss_version.strip()   
            tmp_path = os.path.dirname(tmp_path)           


    def get_product(self):
        print("=====get_product=======")
        product = self.pac_name.split('-')[0]
        print("product:"+product)
        return product


    def get_gms_version(self):
        print("=====get_gms_version=====")
        check_gms = self.pac_name.split('-')[-1].split('_')[0]
        print("check_gms:"+check_gms)
        if check_gms != "gms":
            print("*****Is not gms product*****")
            return ''
        current_cwd = os.getcwd()
        path = os.path.join(current_cwd, "vendor")
        os.chdir(path)
        cmd = "find  -name \"gms.mk\" | xargs grep -ri \"ro.com.google.gmsversion\" | awk -F '=' '{print$NF}'"
        gms_version = os.popen(cmd).read().strip()
        print("gms_version:"+gms_version)
        os.chdir(current_cwd)
        return gms_version

    def out_version(self):
        print("=============== make BT_VERSION start =======================")
        version_path = os.path.join(self.product, VERSION_TXT)
        if os.path.exists(version_path):
            os.remove(version_path)
        with open(version_path, 'w') as out_f:
            out_f.write("["+self.get_pac_name()+"]")
            out_f.write("\n")
            out_f.write("PAC_Time="+self.get_pac_time())
            out_f.write("\n")
            out_f.write("AP="+self.get_ap())
            out_f.write("\n")
            out_f.write("CP0="+self.get_cp0())
            out_f.write("\n")
            out_f.write("CP2="+self.get_cp2())
            out_f.write("\n")
            out_f.write("firmware="+self.get_firmware())
            out_f.write("\n")
            out_f.write("gnss_version="+self.get_gnss_version())
            out_f.write("\n")
            out_f.write("Product="+self.get_product())
            out_f.write("\n")
            out_f.write("gms_version="+self.get_gms_version())
        print("=============== make BT_VERSION end =======================")

    def parse_common_ini(self):
        conf = BMConfigParser()
        common_ini = os.path.join(SCRIPT_PATH, CONFIG_FILE)
        if not os.path.exists(common_ini):
            print("*****not find common.ini*****")
            return ""
        conf.read(common_ini)
        cp0_version = conf.get("cp0_version", "partition")
        cp2_version = conf.get("cp2_version", "partition")
        gnss_version = conf.get("gnss_version", "partition")

        param = [cp0_version,cp2_version,gnss_version]
        return param

    def get_modem_bin(self, modem_key):
        conf = BMConfigParser()
        conf.read(os.path.join(self.product, "pac.ini"))
        modem_keys = conf.options("pac_list")
        if modem_key not in modem_keys:
            return ""
        modem_bin = conf.get("pac_list", modem_key)
        return modem_bin.strip()

    def find_cp2_txt(self, dir):
        if not os.path.exists(dir):
            print("find_cp2_txt--not find "+str(dir))
            return
        for file in os.listdir(dir):
            file_tmp = os.path.join(dir, file)
            if os.path.isfile(file_tmp):
                if file == "version.txt":
                    self.cp2_version_txt = file_tmp
                    break
            else:
                if file == ".git":
                    continue
                self.find_cp2_txt(file_tmp)

    def find_gnss_txt(self, dir):
        if not os.path.exists(dir):
            print("find_gnss_txt--not find "+str(dir))
            return
        for file in os.listdir(dir):
            file_tmp = os.path.join(dir, file)
            if os.path.isfile(file_tmp):
                if file == "version.txt":
                    self.gnss_version_txt = file_tmp
                    break
            else:
                if file == ".git":
                    continue
                self.find_gnss_txt(file_tmp)

class BMConfigParser(ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, option_str):
        return option_str