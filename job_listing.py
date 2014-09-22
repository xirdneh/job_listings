import urllib2, cookielib, urllib, sys, re, os.path, json, time
from cookielib import CookieJar
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import xml.etree.ElementTree as ET

class MyHTMLParser(HTMLParser):
    isIframe = False
    isTable = False
    isTitle = False
    isOpened = False
    isJobNum = False
    isLocation = False
    isForm = False
    isFormNeeded = False
    isICSID = False
    hnewper = False
    hasNext = False
    tableCnt = 0
    data = {'posting_table_string':'', 'jobs':[]}
    row = {}
    re_ptitle = re.compile('^POSTINGTITLE\$[0-9]+')
    re_popened = re.compile('^OPENED\$[0-9]+')
    re_jobnum = re.compile('^JOBNUMBER\$[0-9]+')
    re_location = re.compile('^HRS_LOCATION_DESCR\$[0-9]+')
    def tagToString(self, tag, attrs):
        ret = '<' + tag + ' '
        for attr in attrs:
            ret += attr[0] + '=' + attr[1] + ' '
        ret += '>'
        return ret
    def handle_starttag(self, tag, attrs):
        if tag == 'iframe':
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'ptifrmtgtframe':
                    self.isIframe = True;
                if attr[0] == 'src' and self.isIframe:
                    self.data['posting_page_src'] = attr[1]
                    self.isIframe = False
        if tag == 'table':
            self.tableCnt = self.tableCnt + 1
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'ACE_HRS_APPL_WRK_HRS_JOB_POST_GPB':
                    self.isTable = True
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'id' and self.re_ptitle.match(attr[1]):
                    self.row['job_element_id'] = attr[1]
                    self.isTitle = True
                if attr[0] == 'id' and attr[1] == 'HRS_APPL_WRK_HRS_LST_NEXT':
                    log = open('log.file', 'a')
                    log.write(time.strftime("%c") + " Next Found \n")
                    log.close()
                    self.hasNext = True
        if tag == 'span':
            for attr in attrs:
                if attr[0] == 'id':
                    if self.re_popened.match(attr[1]):
                        self.isOpened = True
                    elif self.re_jobnum.match(attr[1]):
                        self.isJobNum = True
                    elif self.re_location.match(attr[1]):
                        self.isLocation = True
        if tag == 'form':
            self.isForm = True
            for attr in attrs:
                if attr[0] == 'name' and attr[1] == 'win0':
                    self.isFormNeeded = True
                if attr[0] == 'action' and self.isFormNeeded:
                    self.data['form_action'] = attr[1]
        if tag == 'input':
            for attr in attrs:
                if attr[0] == 'name':
                    if attr[1] == 'ICSID':
                        self.isICSID = True
                    if attr[1] == 'HRS_CE_JO_EXT_I$hnewpers$0':
                        self.hnewper = True
                    #print '\033[95m Input Name: {0}'.format(attr[1])
                if attr[0] == 'value':
                    if self.isICSID:
                        self.data['ICSID'] = attr[1]
                        self.isICSID = False
                    if self.hnewper:
                        self.data['hnewper'] = attr[1]
                        self.hnewper = False
                    #print '\033[93m Input value: {0}'.format(attr[1])
        if self.isTable:
            self.data['posting_table_string'] += self.tagToString(tag, attrs)
    def handle_data(self, data):
        if self.isTable:
            self.data['posting_table_string'] += data
        if self.isTitle:
            if 'title' in self.row:
                self.row['title'] += self.unescape(data.decode('windows-1252').encode('UTF-8'))
            else:
                self.row['title'] = self.unescape(data.decode('windows-1252').encode('UTF-8'))
        if self.isOpened:
            self.row['date'] = self.unescape(data.decode('windows-1252').encode('UTF-8'))
        if self.isJobNum:
            self.row['job_id'] = self.unescape(data.decode('windows-1252').encode('UTF-8'))
        if self.isLocation:
            self.row['location'] = self.unescape(data.decode('windows-1252').encode('UTF-8'))
    def handle_endtag(self, tag):
        if self.isTable:
            self.data['posting_table_string'] += '</' + tag + '>'
        if tag == 'table':
            self.tableCnt = self.tableCnt - 1
            if self.tableCnt <= 0:
                self.isTable = False
        if tag == 'a' and self.isTitle:
            self.isTitle = False;
        if tag == 'span':
            if self.isOpened:
                self.isOpened = False
            elif self.isJobNum:
                self.isJobNum = False
            elif self.isLocation:
                self.isLocation = False
                self.data['jobs'].append(self.row)
                log = open('log.file', 'a')
                log.write(time.strftime("%c") + " " + str(self.row) + "\n")
                self.row = {}
        if tag == 'form':
            self.isForm = False
            self.isFormNeeded = False

def main(argv):
    url = 'https://zhr-candidate.shared.utsystem.edu/psp/ZHRPRDCG/EMPLOYEE/HRMS/c/HRS_HRAM.HRS_CE.GBL/?tab=PAPP_GUEST&SiteId=20'
    page_cnt = 0
    obj_index = 0
    #url = 'https://zhr-candidate.shared.utsystem.edu/psp/ZHRPRDCG/EMPLOYEE/HRMS/c/HRS_HRAM.HRS_CE.GBL/?tab=PAPP_GUEST&SiteId=8'
    cj = CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)
    response = urllib2.urlopen(url)
    html = response.read()
    parser = MyHTMLParser()
    parser.feed(html)
    response = urllib2.urlopen(parser.data['posting_page_src'])
    html = response.read()
    parser.feed(html)

    jls = {"data":[{"date":"","job_id":"" }]}
    if os.path.isfile('/home/theusbar/utrg_jobs/job_listing.json'):
        jlf = open('/home/theusbar/utrg_jobs/job_listing.json', 'r')
        jls = json.load(jlf)
        jlf.close()
    #Check if the last job is different from the last job that we have saved. If it is then we have new listings. 
    form_values = {
        "ICAJAX" : "1",
        "ICNAVTYPEDROPDOWN" : "0",
        "ICType" : "Panel",
        "ICElementNum" : "0",
        "ICStateNum" : "0",
        "ICAction" : "",
        "ICXPos" : "0",
        "ICYPos" : "0",
        "ResponsetoDiffFrame" : "-1",
        "TargetFrameName" : "None",
        "FacePath" : "None",
        "ICFocus" : "",
        "ICSaveWarningFilter" : "0",
        "ICChanged" : "-1",
        "ICResubmit" : "0",
        "ICSID" : parser.data['ICSID'],
        "ICActionPrompt" : "false",
        "ICFind" : "",
        "ICAddCount" : "",
        "ICAPPCLSDATA" : "",
        "HRS_CE_JO_EXT_I$hnewpers$0":parser.data['hnewper'],
        "HRS_APP_SRCHDRV_HRS_APP_KEYWORD" : "",
        "HRS_APP_SRCHDRV_HRS_POSTED_WTN" : "M",
        "HRS_APPL_WRK_HRS_OPRNAME" : "",
        "HRS_APPL_WRK_HRS_OPRPSWD" : "",
        "SEELCT$chk$0":"N", 
        "SEELCT$chk$1":"N",
        "SEELCT$chk$2":"N",
        "SEELCT$chk$3":"N",
        "SEELCT$chk$4":"N"
    }

    if jls['data'][0]['date'] != unicode(parser.data['jobs'][0]['date']) or jls['data'][0]['job_id'] != unicode(parser.data['jobs'][0]['job_id']):
        #Get details for jobs
        pt_cnt = 0
        for ind in range(obj_index, len(parser.data['jobs'])):
            page_cnt = page_cnt + 1
            form_values['ICStateNum'] = str(page_cnt)
            form_values['ICAction'] =  'POSTINGTITLE$' + str(pt_cnt)
            pt_cnt = pt_cnt + 1
            obj_index = obj_index + 1
             
            data = urllib.urlencode(form_values)
            #print "Referrer: {0}".format(parser.data['posting_page_src'])
            request = urllib2.Request(url=parser.data['form_action'], data=data)
            request.add_header('Referer', parser.data['posting_page_src'])
            request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36')
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
            request.add_header('Host', 'zhr-candidate.shared.utsystem.edu')
            request.add_header('Origin', 'https://zhr-candidate.shared.utsystem.edu')
            request.add_header('Connection', 'keep-alive')
            request.add_header('Accept','*/*')
            response = urllib2.urlopen(request)
            det_html = response.read()
            tree = ET.fromstring(det_html)
            fields = tree.findall('FIELD')
            for field in fields:
                if field.attrib['id'] == 'win0divPAGECONTAINER':
                    parser.data['jobs'][ind]['details_html'] = field.text
                    dets = open(parser.data['jobs'][ind]['job_id'] + '_details.html', 'w')
                    dets.write(field.text.encode('UTF-8'))
                    dets.close()
                   

            page_cnt = page_cnt + 1
            form_values['ICStateNum'] = str(page_cnt)
            form_values['ICAction'] = 'HRS_CE_WRK2_HRS_REF_JB_RETURN'
            data = urllib.urlencode(form_values)
            #print "Referrer: {0}".format(parser.data['posting_page_src'])
            request = urllib2.Request(url=parser.data['form_action'], data=data)
            request.add_header('Referer', parser.data['posting_page_src'])
            request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36')
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
            request.add_header('Host', 'zhr-candidate.shared.utsystem.edu')
            request.add_header('Origin', 'https://zhr-candidate.shared.utsystem.edu')
            request.add_header('Connection', 'keep-alive')
            request.add_header('Accept','*/*')
            response = urllib2.urlopen(request)
    
        #Check if the Next link is available, if it is then we need to retrieve the rest of the listings. 
        while(parser.hasNext):
            #print "Going to NExt using {0}".format(parser.data['form_action'])
            page_cnt = page_cnt + 1
            form_values['ICStateNum'] = str(page_cnt)
            form_values['ICAction'] = 'HRS_APPL_WRK_HRS_LST_NEXT' 
            #print "ICSID :".format(parser.data['ICSID'])
            #print "DATA: {0}".format(form_values)
            data = urllib.urlencode(form_values)
            #print "Referrer: {0}".format(parser.data['posting_page_src'])
            request = urllib2.Request(url=parser.data['form_action'], data=data)
            request.add_header('Referer', parser.data['posting_page_src'])
            request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36')
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
            request.add_header('Host', 'zhr-candidate.shared.utsystem.edu')
            request.add_header('Origin', 'https://zhr-candidate.shared.utsystem.edu')
            request.add_header('Connection', 'keep-alive')
            request.add_header('Accept','*/*')
            #print "Method: {0}".format(request.get_method())
            response = urllib2.urlopen(request)
            #print response.getcode()
            xml = response.read()
            log = open('log_r', 'w')
            log.write(xml)
            log.close()
            tree = ET.fromstring(xml)
            fields = tree.findall("FIELD")
            if len(fields) > 1:
                for field in fields:
                    if field.attrib['id'] == 'win0divHRS_APPL_WRK_HRS_LST_NEXT':
                        parser.feed(field.text)
                    elif field.attrib['id'] == 'win0divHRS_CE_JO_EXT_I$0':
                        html = field.text
            else:
                html = fields[0].text
            log = open('log', 'w') 
            log.write(html)
            log.close()
            parser.hasNext = False
            parser.feed(html)
            #print "HasNext {0}".format(parser.hasNext)

            pt_cnt = 0
            for ind in range(obj_index, len(parser.data['jobs'])):
                page_cnt = page_cnt + 1
                form_values['ICStateNum'] = str(page_cnt)
                form_values['ICAction'] =  'POSTINGTITLE$' + str(pt_cnt)
                pt_cnt = pt_cnt + 1
                obj_index = obj_index + 1
                 
                data = urllib.urlencode(form_values)
                #print "Referrer: {0}".format(parser.data['posting_page_src'])
                request = urllib2.Request(url=parser.data['form_action'], data=data)
                request.add_header('Referer', parser.data['posting_page_src'])
                request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36')
                request.add_header('Content-Type', 'application/x-www-form-urlencoded')
                request.add_header('Host', 'zhr-candidate.shared.utsystem.edu')
                request.add_header('Origin', 'https://zhr-candidate.shared.utsystem.edu')
                request.add_header('Connection', 'keep-alive')
                request.add_header('Accept','*/*')
                response = urllib2.urlopen(request)
                det_html = response.read()
                tree = ET.fromstring(det_html)
                fields=tree.findall('FIELD')
                for field in fields:
                    if field.attrib['id'] == 'win0divPAGECONTAINER':
                        parser.data['jobs'][ind]['details_html'] = field.text
                        dets = open(parser.data['jobs'][ind]['job_id'] + '_details.html', 'w')
                        dets.write(field.text.encode('UTF-8'))
                        dets.close()
                                
                page_cnt = page_cnt + 1
                form_values['ICStateNum'] = str(page_cnt)
                form_values['ICAction'] = 'HRS_CE_WRK2_HRS_REF_JB_RETURN'
                data = urllib.urlencode(form_values)
                #print "Referrer: {0}".format(parser.data['posting_page_src'])
                request = urllib2.Request(url=parser.data['form_action'], data=data)
                request.add_header('Referer', parser.data['posting_page_src'])
                request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36')
                request.add_header('Content-Type', 'application/x-www-form-urlencoded')
                request.add_header('Host', 'zhr-candidate.shared.utsystem.edu')
                request.add_header('Origin', 'https://zhr-candidate.shared.utsystem.edu')
                request.add_header('Connection', 'keep-alive')
                request.add_header('Accept','*/*')
                response = urllib2.urlopen(request)
         
        #Write the new listings to the file.
        f = open('/home/theusbar/utrg_jobs/job_listing.json', 'w')
        f.write("{\"data\": " + json.dumps(parser.data['jobs']) + "}")
        f.close()
        #send the email
        from_add = 'sendmail_theusbar@web310.webfaction.com'
        to_add = ['xirdneh@gmail.com', 'balandranocoronej@utpa.edu']
        s = SMTP()
        s.connect('smtp.webfaction.com')
        s.login('theusbar', 'tsmbat')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = time.strftime("%c") + " Job Listings"
        msg['From'] = from_add
        msg['To'] = 'xirdneh@gmail.com'
        txt_msg = '--Date-- | --Job title-- | --Job ID-- | --Location--'
        for job in parser.data['jobs']:
            txt_msg += job['date'] + '|' + job['title'] + '|' + job['job_id'] + '|' + job['location'] + '|'
        html_msg = ('<html><head>' 
                   '</head><body>')
        html_msg = ('<table style = "border-collapse: collapse; border-spacing: 0; empty-cells: show; border: 1px solid #cbcbcb;">'
                    '<thead style = "background-color:#eee; font-weight:bold;"><tr><td style="border: 1px solid #cbcbcb">Date</td>'
                    '<td style="border: 1px solid #cbcbcb">Job Title</td>'
                    '<td style="border: 1px solid #cbcbcb">Job ID</td>'
                    '<td style="border: 1px solid #cbcbcb">Location</td></tr></thead><tbody>')
        for job in parser.data['jobs']:
            html_msg += '<tr><td style="border: 1px solid #cbcbcb">' + job['date'] + '</td><td style="border: 1px solid #cbcbcb">' + job['title'] + '</td><td style="border: 1px solid #cbcbcb">' + job['job_id'] + '</td><td style="border: 1px solid #cbcbcb">' + job['location'] + '</td></tr>'
        html_msg += '</tbody></table></body></html>'
        part1 = MIMEText(txt_msg, 'plain')
        part2 = MIMEText(html_msg, 'html')
        msg.attach(part1)
        msg.attach(part2)
        s.sendmail(from_add, to_add, msg.as_string())
        log = open('log.file', 'a')
        log.write(time.strftime("%c") + " Message Set \n")
        log.close()
    else:
        log = open('log.file', 'a')
        log.write(time.strftime("%c") + " No new jobs \n")
        log.close()

if __name__ == "__main__":
    main(sys.argv[1:])
