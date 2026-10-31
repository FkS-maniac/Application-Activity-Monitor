import csv

def export_csv(path,headers,rows):
 with open(path,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f,delimiter=';');w.writerow(headers);w.writerows(rows)
