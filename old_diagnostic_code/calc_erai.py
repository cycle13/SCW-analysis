#A driver to load ERA-Interim data and calculate convective parameters. Made parallel in python

#Must call "source activate pycat" if calculating DCAPE. DCAPE calculation requires numpy 1.16.0

from calc_model import *
from multiprocessing import Pool

if __name__ == "__main__":

	dates = []
	for y in np.arange(1979,2018):
		for m in [1,2,3,4,5,6,7,8,9,10,11,12]:
		    if (m != 12):
			dates.append([dt.datetime(y,m,1,0,0,0),\
				dt.datetime(y,m+1,1,0,0,0)-dt.timedelta(hours = 6)])
		    else:
			dates.append([dt.datetime(y,m,1,0,0,0),\
				dt.datetime(y+1,1,1,0,0,0)-dt.timedelta(hours = 6)])
	dates = np.array(dates)

	param = ["ml_cape","ml_cin","mu_cin","mu_cape","srh01","srh03","srh06","scp",\
		"stp","ship","mmp","relhum850-500","vo10","lr1000","lcl",\
		"relhum1000-700","s06","s0500","s01","s03",\
		"cape*s06","dcp","td850","td800","td950","dcape","mlm","dlm",\
		"dcape*cs6","mlm+dcape","mlm*dcape*cs6","mf","sf","cond"]
	model = "erai"
	cape_method = "wrf_par"
	method = "domain"
	region = "sa_small"

	for date in dates:
		[param,param_out,lon,lat,date_list] = \
			calc_model(model,model,method,date,param,True,region,cape_method)	

