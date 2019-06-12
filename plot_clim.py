import xarray
import matplotlib
matplotlib.use("Agg")
import netCDF4 as nc
from plot_param import *
from barra_r_fc_read import get_terrain as get_barra_r_terrain
from barra_r_fc_read import get_lat_lon as get_barra_r_lat_lon
from barra_ad_read import get_lat_lon as get_barra_ad_lat_lon
from erai_read import get_lat_lon, drop_erai_fc_duplicates
from obs_read import read_clim_ind
from scipy.stats import spearmanr as rho

def clim(domain,model,year_range,var_list,seasons=[[1,2,3,4,5,6,7,8,9,10,11,12]],levels=False,\
		plot_trends=False):
	
	f = load_ncdf(domain,model,year_range,var_list)
	lon = f.variables["lon"][:]
	lat = f.variables["lat"][:]
	time = nc.num2date(f.variables["time"][:],f.variables["time"].units)
	months = np.array([t.month for t in time])

	m = Basemap(llcrnrlon = lon.min(), llcrnrlat = lat.min(), urcrnrlon = lon.max(), \
				urcrnrlat = lat.max(), projection="cyl", resolution = "l")

	print("INFO: Plotting...")
	for var in var_list:

	    print(var)
	    if plot_trends:
		dmean,daily_dates = netcdf_resample(f,time,var,model,"mean")
		daily_months = np.array([t.month for t in daily_dates])
		daily_years = np.array([t.year for t in daily_dates])

	    for season in seasons:

		print(season)

		#IF DOING CORRELATIONS WITH CLIMATE INDICES, MAY HAVE TO RESAMPLE TO DAILY MEAN.
		#CURRENTLY, DO FOR 6-HOURLY DATA

		data = f.variables[var][np.in1d(months,np.array(season))]
		print("NAN REPORT: "+str((data==np.nan).sum()))
		mean = np.nanmean(data,axis=0)
		plot_clim(f,m,lat,lon,mean,var,model,domain,year_range,season=season,levels=levels)

		if plot_trends:
			t1 = np.array(daily_dates) <= dt.datetime(1998,12,31)
			t2 = np.array(daily_dates) >= dt.datetime(1998,1,1)
			dmean_season1 = dmean[np.in1d(daily_months,np.array(season)) & (t1)]
			dmean_season2 = dmean[np.in1d(daily_months,np.array(season)) & (t2)]
			a = np.mean(dmean_season1,axis=0)
			b = np.mean(dmean_season2,axis=0)
			trend = ((b - a) / a) * 100
		
def load_xarray(var,year_range,start_lon,start_lat,end_lon,end_lat,plevel=False):

	#Function to load ERA-Interim directly from the ub4 directory. Have to use xarray to load all files
	#at once

	#Note, if loading pressure level data (e.g. ta850), the whole era-interim dataset takes too long to load
	# with xarray.open_mfdataset. So, we loop over each file, extract the pressure level we want, and append
	# to a numpy array. To save time, this array is saved to the eg3 /g/data directory as a netcdf file, which
	# can be loaded if it has already been processed for the right variable/pressure level/time period.

	fnames = list()
	if var in ["tas","ta2d"]:
		for y in np.arange(year_range[0],year_range[1]+1):
			fnames.extend(glob.glob("/g/data/ub4/erai/netcdf/6hr/atmos/oper_an_sfc/v01/"+var+"/"+var+\
			"*"+str(y)+"*.nc"))
	elif var == "tos":
		for y in np.arange(year_range[0],year_range[1]+1):
			fnames.extend(glob.glob("/g/data/ub4/erai/netcdf/6hr/ocean/oper_an_sfc/v01/"+var+"/"+var+\
			"*"+str(y)+"*.nc"))
	else:
		for y in np.arange(year_range[0],year_range[1]+1):
			fnames.extend(glob.glob("/g/data/ub4/erai/netcdf/6hr/atmos/oper_an_pl/v01/"+var+"/"+var+\
			"*"+str(y)+"*.nc"))
	fnames.sort()
	
	#Get lat/lon inds
	lon,lat = get_lat_lon()
	lon_ind = np.where((lon >= start_lon) & (lon <= end_lon))[0]
	lat_ind = np.where((lat >= start_lat) & (lat <= end_lat))[0]
	lon = lon[lon_ind]
	lat = lat[lat_ind]

	#Load data
	if var in ["tas","ta2d","tos"]:
		f = xarray.open_mfdataset(fnames,decode_times=False)
		values = f.data_vars[var][:,lat_ind,lon_ind].values
	else:
	    fname = "/g/data/eg3/ab4502/ExtremeWind/sa_small/erai_"+var+str(plevel)+"_"+str(year_range[0])+"_"+\
		str(year_range[1])+".nc"
	    if not os.path.isfile(fname):
		print("This variable has not yet been extracted for this pressure level. Processing...\n")
		values = np.empty((0,len(lat_ind),len(lon_ind)))
		for i in np.arange(len(fnames)):
			print(i)
			f = xarray.open_dataset(fnames[i],decode_times=False)
			if i == 0:
				lev = f.coords["lev"].values
			temp = f.data_vars[var][:,\
				np.where(np.array(abs(lev-plevel))==np.array(abs(lev-plevel)).min())[0][0],\
				lat_ind,lon_ind].values
			values = np.concatenate((values,temp),axis=0)
			f.close()
		out_file = nc.Dataset(fname,"w",format="NETCDF4_CLASSIC")
		time_dim = out_file.createDimension("time",None)
		lat_dim = out_file.createDimension("lat",len(lat_ind))
		lon_dim = out_file.createDimension("lon",len(lon_ind))
		out_var = out_file.createVariable(var+str(plevel),lat.dtype,("time","lat","lon"))
		out_var[:] = values
		out_file.close()
	    else:
		values = nc.Dataset(fname).variables[var+str(plevel)][:]
		
	#Format times
	ref = dt.datetime(1900,1,1,0,0,0)
	if var in ["tas","ta2d"]:
		times = f.coords["time"].data
		times = nc.num2date(times,nc.Dataset("/g/data/ub4/erai/netcdf/6hr/atmos/oper_an_sfc/v01/"+var+\
			"/"+var+"_6hrs_ERAI_historical_an-sfc_19790101_19790131.nc").variables["time"].units)
	elif var == "tos":
		times = f.coords["time"].data
		times = nc.num2date(times,nc.Dataset("/g/data/ub4/erai/netcdf/6hr/ocean/oper_an_sfc/v01/"+var+\
			"/"+var+"_6hrs_ERAI_historical_an-sfc_19790101_19790131.nc").variables["time"].units)
	else:
		times = nc.num2date(xarray.open_mfdataset(fnames,decode_times=False).coords["time"].data,\
			nc.Dataset("/g/data/ub4/erai/netcdf/6hr/atmos/oper_an_pl/v01/"+var+\
			"/"+var+"_6hrs_ERAI_historical_an-pl_19790101_19790131.nc").variables["time"].units)

	return [values, times, lat, lon]

def load_ncdf(domain,model,year_range,var_list=False):

	#Load netcdf files of convective parameters

	print("INFO: Loading data for "+model+" on domain "+domain+" between "+str(year_range[0])+\
		" and "+str(year_range[1]))

	#Create filenames in year range
	fnames = list()
	for y in np.arange(year_range[0],year_range[1]+1):
		fnames.extend(glob.glob("/g/data/eg3/ab4502/ExtremeWind/"+domain+"/"+model+"/"+model+\
			"_"+str(y)+"*.nc"))
	fnames.sort()
	#Only get dataset for var_list (unless False). For BARRA-R, inconsistent name, for wg, need to change 
	file_vars = np.array(nc.Dataset(fnames[0]).variables.keys())
	if var_list != False:
	    if (model == "barra_r_fc") | (model == "erai_fc"):
		exclude_vars = file_vars[~(np.in1d(file_vars,var_list)) & ~(file_vars=="lon") & \
			~(file_vars=="lat") & ~(file_vars=="time")]
	    else:
		exclude_vars = file_vars[~(np.in1d(file_vars,var_list)) & ~(file_vars=="lon") & \
			~(file_vars=="lat") & ~(file_vars=="time") & ~(file_vars=="ml_cape") & \
			~(file_vars=="s06")]
	    return(nc.MFDataset(fnames,exclude=exclude_vars))
	else:
	    return(nc.MFDataset(fnames))

def daily_resample(f,time,var,model,method,ftype="netcdf"):

	#Resample a file from sub-daily to a daily max array
	#File can either be "netcdf" or "xarray"

	if ftype == "netcdf":
		if var == "mlcape*s06":
			a = (f.variables["ml_cape"][:]) * np.power(f.variables["s06"][:],1.67)
		else:
			a =  f.variables[var][:]
		if model == "erai_fc":
			a,time = drop_erai_fc_duplicates(a,time)
	else:
		#OR ELSE, IS A ERAI ANALYSIS, ALREADY EXTRACTED
		a = f

	years = np.array([t.year for t in time])
	months = np.array([t.month for t in time])
	days = np.array([t.day for t in time])
	hours = np.array([t.hour for t in time])
	ymd,idx = np.unique([dt.datetime.strftime(t,"%Y%m%d") for t in time],return_index=True)
	daily_dates = [dt.datetime.strptime(t,"%Y%m%d") for t in ymd]
	daily_dates = daily_dates[0:-1]

	#dmax = np.empty((len(daily_dates),f.variables["lat"].shape[0],f.variables["lon"].shape[0]))
	#for i in np.arange(0,len(daily_dates)):
	#	year_ind = daily_dates[i].year == years
	#	month_ind = daily_dates[i].month == months
	#	day_ind = daily_dates[i].day == days
	#	if var == "mlcape*s06":
	#		temp_arr = (f.variables["ml_cape"][(year_ind)&(month_ind)&(day_ind)]) * \
	#			np.power(f.variables["s06"][(year_ind)&(month_ind)&(day_ind)],1.67)
	#	else:
	#		temp_arr = f.variables[var][(year_ind)&(month_ind)&(day_ind)]
	#	if ("wg" in var) or ("gust" in var):
	#		temp_arr = wind_gust_filter(temp_arr)
	#	dmax[i] = np.nanmax(temp_arr,axis=0)
	a = np.split(a,idx[1:-1],axis=0)
	if method=="max":
		dmax = np.stack([np.nanmax(i,axis=0) for i in a])
	elif method=="mean":
		dmax = np.stack([np.nanmean(i,axis=0) for i in a])
	else:
		raise ValueError("METHOD MUST BE ""max"" or ""mean""")

	if model=="erai_fc":
		return(dmax.data,daily_dates)
	else:
		return(dmax,daily_dates)
	

def daily_max_clim(domain,model,year_range,threshold=False,var_list=False,seasons=[[1,2,3,4,5,6,7,8,9,10,11,12]],\
			plot_trends=False,levels=False,trend_levels=np.linspace(-50,50,11),plot_corr=False,\
			n_boot=1000,trend_on_cond_days=False):
	#Plot daily max climatology
	#Re-sample to daily maximum first
	#If var = False, plot all vars. Else, pass a list of var names

	#Set up domain
	if domain == "aus":
	    start_lat = -44.525; end_lat = -9.975; start_lon = 111.975; end_lon = 156.275
	elif domain == "sa_small":
	    start_lat = -38; end_lat = -26; start_lon = 132; end_lon = 142
	elif domain == "sa_large":
	    start_lat = -40; end_lat = -24; start_lon = 112; end_lon = 156
	m = Basemap(llcrnrlon = start_lon, llcrnrlat = start_lat, urcrnrlon = end_lon, \
				urcrnrlat = end_lat, projection="cyl", resolution = "l")

	#If we are looking at 2 m air temp or dew point, then get the data straight from the ERA-Interim
	# directory, rather than from the calculated convective parameter directory
	if ("tas" in var_list) | ("ta2d" in var_list) | ("ta850" in var_list) | ("dp850" in var_list)\
		 | ("ta700" in var_list) | ("dp700" in var_list) | ("tos" in var_list):
		if trend_on_cond_days:
			f = load_ncdf(domain,model,year_range,["ml_cape","s06","dcape","dlm"])
			lon = f.variables["lon"][:]
			lat = f.variables["lat"][:]
			time = nc.num2date(f.variables["time"][:],f.variables["time"].units)
			mlcape,daily_dates = daily_resample(f,time,"ml_cape",model,"max")
			dcape,daily_dates = daily_resample(f,time,"dcape",model,"max")
			s06,daily_dates = daily_resample(f,time,"s06",model,"max")
			dlm,daily_dates = daily_resample(f,time,"dlm",model,"max")
			sf = ((s06>30) & (dcape>0) & (dcape<500) & (dlm>=26) )                
			wf = ((mlcape>120) & (dcape>250) & (dlm<26) )     
			dmax = sf  | wf 
			dmax = dmax * 1.0; sf = sf * 1.0; wf = wf * 1.0
			cond = np.copy(dmax)
	else:
		if ("cond" in var_list) | (trend_on_cond_days):
			f = load_ncdf(domain,model,year_range,["cond","mf","sf"])
		else:
			f = load_ncdf(domain,model,year_range,var_list)
		lon = f.variables["lon"][:]
		lat = f.variables["lat"][:]
		if var_list == False:
			var_list = np.array([str(f.variables.items()[i][0]) for i in np.arange(0,\
				len(f.variables.items()))])
			var_list = var_list[~(var_list=="time") & ~(var_list=="lat") & ~(var_list=="lon")]
		time = nc.num2date(f.variables["time"][:],f.variables["time"].units)

	#Resample to daily max
	print("Resampling gridded data to daily max...")
	for v in np.arange(0,len(var_list)):
		print(var_list[v])

		if (var_list[v] == "cond"):
			#mlcape,daily_dates = daily_resample(f,time,"ml_cape",model,"max")
			#dcape,daily_dates = daily_resample(f,time,"dcape",model,"max")
			#s06,daily_dates = daily_resample(f,time,"s06",model,"max")
			#dlm,daily_dates = daily_resample(f,time,"dlm",model,"max")
			#sf = ((s06>30) & (dcape>0) & (dcape<500) & (dlm>=26) )                
			#wf = ((mlcape>120) & (dcape>250) & (dlm<26) )     
			dmax,daily_dates = daily_resample(f,time,"cond",model,"max")
			wf,daily_dates = daily_resample(f,time,"mf",model,"max")
			sf,daily_dates = daily_resample(f,time,"sf",model,"max")
			#dmax = sf  | wf 
			#dmax = dmax * 1.0; sf = sf * 1.0; wf = wf * 1.0
			cond = np.copy(dmax)
		elif var_list[v] in ["tas","ta2d","tos"]:
			dmax, daily_dates, lat, lon = load_xarray(var_list[v],year_range,start_lon,start_lat,\
				end_lon,end_lat)
			dmax,daily_dates = daily_resample(dmax,daily_dates,None,"erai","max",ftype="xarray")
		elif var_list[v] in ["ta850"]:
			dmax, daily_dates, lat, lon = load_xarray("ta",year_range,start_lon,start_lat,\
				end_lon,end_lat,85000)
			dmax,daily_dates = daily_resample(dmax,daily_dates,None,"erai","max",ftype="xarray")
		elif var_list[v] in ["ta700"]:
			dmax, daily_dates, lat, lon = load_xarray("ta",year_range,start_lon,start_lat,\
				end_lon,end_lat,70000)
			dmax,daily_dates = daily_resample(dmax,daily_dates,None,"erai","max",ftype="xarray")
		elif var_list[v] in ["dp850"]:
			hur_dmax, daily_dates, lat, lon = load_xarray("hur",year_range,start_lon,start_lat,\
				end_lon,end_lat,85000)
			ta_dmax, daily_dates, lat, lon = load_xarray("ta",year_range,start_lon,start_lat,\
				end_lon,end_lat,85000)
			dmax,daily_dates = daily_resample(get_dp(ta_dmax,hur_dmax),daily_dates,None,\
				"erai","max",ftype="xarray")
		elif var_list[v] in ["dp700"]:
			hur_dmax, daily_dates, lat, lon = load_xarray("hur",year_range,start_lon,start_lat,\
				end_lon,end_lat,70000)
			ta_dmax, daily_dates, lat, lon = load_xarray("ta",year_range,start_lon,start_lat,\
				end_lon,end_lat,70000)
			dmax,daily_dates = daily_resample(get_dp(ta_dmax,hur_dmax),daily_dates,None,\
				"erai","max",ftype="xarray")
		else:
			dmax,daily_dates = daily_resample(f,time,var_list[v],model,"max")
		daily_months = np.array([t.month for t in daily_dates])
		daily_years = np.array([t.year for t in daily_dates])

		print("Plotting for each season...")
		for season in seasons:
			print(season)

			dmax_season = dmax[np.in1d(daily_months,np.array(season))]

			#PLOT MEAN
			#If a threshold is given, then plot the number of days which exceed this threshold
			if threshold != False:
				exceeds = dmax_season > threshold[v]
				exceeds_sum = (np.sum(exceeds,axis=0)) / float(((year_range[1]-year_range[0])+1))
				try:
				    plot_clim(f,m,lat,lon,exceeds_sum,var_list[v],model,domain,year_range,season,\
					threshold=threshold[v],levels=levels[v])
				except:
				    plot_clim(f,m,lat,lon,exceeds_sum,var_list[v],model,domain,year_range,season,\
					threshold=threshold[v],levels=levels)
			#If no threshold is given...
			else:
			   #For COND, plot the number of times condition is met, also plot "sf", "mf" and "wfper"
			   if var_list[v] == "cond":
				sf_season = sf[np.in1d(daily_months,np.array(season))]
				wf_season = wf[np.in1d(daily_months,np.array(season))]
				vals = [dmax_season,sf_season,wf_season,None]
				cond_list = ["cond","sf","wf","wfper"]
				levels_list = [np.arange(0,42.5,2.5),np.arange(0,21.125,1.25),np.arange(0,42.5,2.5),\
							np.arange(0,110,10)]
				for i in np.arange(0,len(vals)):
				    if cond_list[i] == "wfper":
					exceeds_sum = np.sum(vals[2],axis=0)/np.sum(vals[0],axis=0) * 100
					plot_clim(f,m,lat,lon,exceeds_sum,cond_list[i],model,\
						domain,year_range,season,\
						threshold=threshold,levels=levels_list[i])
				    else:
					exceeds_sum = np.sum(vals[i],axis=0) \
						/ float(((year_range[1]-year_range[0])+1))
					plot_clim(f,m,lat,lon,exceeds_sum,cond_list[i],model,domain,\
						year_range,season,\
						threshold=threshold,levels=levels_list[i])
			   #For surface temp and dew point, plot mean 
			   elif var_list[v] in ["tas","ta2d","tos"]:
				try:
				    plot_clim(None,m,lat,lon,dmax_season.mean(axis=0),var_list[v],model,domain,\
					year_range,season,levels=levels[v])
				except:
				    plot_clim(None,m,lat,lon,dmax_season.mean(axis=0),var_list[v],model,domain,\
					year_range,season,threshold=threshold,levels=levels)
			   #For pressure-level temperature and humidity, plot mean
			   elif var_list[v] in ["ta850","ta700","dp850","dp700"]:
				try:
				    plot_clim(None,m,lat,lon,dmax_season.mean(axis=0),var_list[v],model,domain,\
					year_range,season,levels=levels[v])
				except:
				    plot_clim(None,m,lat,lon,dmax_season.mean(axis=0),var_list[v],model,domain,\
					year_range,season,threshold=threshold,levels=levels)
			   #Or else, try and plot the mean
			   else:
				exceeds_sum = np.sum(dmax_season,axis=0) / float(((year_range[1]-year_range[0])+1))
				try:
				    plot_clim(f,m,lat,lon,exceeds_sum,var_list[v],model,domain,year_range,season,\
					threshold=threshold,levels=levels[v])
				except:
				    plot_clim(f,m,lat,lon,exceeds_sum,var_list[v],model,domain,year_range,season,\
					threshold=threshold,levels=levels)

			#PLOT TRENDS
			if plot_trends:
			   #Define the first and second half of the period 1979-2017
			   t1 = np.array(daily_dates) <= dt.datetime(1998,12,31)
			   t2 = np.array(daily_dates) >= dt.datetime(1998,1,1)
			   #For the conditional parameter, as well as "sf" and "wf"
			   if var_list[v] == "cond":
				vals = [dmax,sf,wf]
				cond_list = ["cond","sf","wf"]
				for c in np.arange(0,len(vals)):
					a = vals[c][np.in1d(daily_months,np.array(season)) & (t1)]
					b = vals[c][np.in1d(daily_months,np.array(season)) & (t2)]
					trend = (np.sum(b,axis=0) - np.sum(a,axis=0)) / np.nansum(a,axis=0).astype(float) * 100
					trend[(np.nansum(a,axis=0)==0)&(np.nansum(b,axis=0)>0)] = 1000
					if n_boot > 0:
						sig = np.empty((trend.shape[0],trend.shape[1]))
						for i in np.arange(0,a.shape[1]):
						   for j in np.arange(0,a.shape[2]):
							p = hypothesis_test(a[:,i,j],b[:,i,j],n_boot)
							sig[i,j] = p
					x,y=np.meshgrid(lon,lat)
					plt.figure()
					m.drawcoastlines()
					m.contourf(x,y,trend,cmap=cm.RdBu_r,levels=trend_levels,extend="both")
					m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
							labels=[True,False,False,True])
					m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
							labels=[True,False,True,False])
					if n_boot > 0:
						plt.plot(x[np.where(sig<=0.05)],y[np.where(sig<=0.05)],"ko")
					else:
						add_towns(m)
					plt.colorbar()
					plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/trends/contour_"+\
						model+"_"+cond_list[c]+"_"+str(season[0])+"_"+str(season[-1])+"_"+str(year_range[0])+"_"+\
						str(year_range[1])+".png",bbox_inches="tight")

					#Now, do a spatial trend
					spatial_trends(cond_list[c],a, b, [137,-35.5,139,-32], x, y, year_range)

			   #For temperature and humidity
			   elif var_list[v] in ["tas","ta2d","ta850","ta700","dp850","dp700","tos"]:
				a = dmax[np.in1d(daily_months,np.array(season)) & (t1)]
				b = dmax[np.in1d(daily_months,np.array(season)) & (t2)]
				trend = (np.nanmean(b,axis=0) - np.nanmean(a,axis=0))
				if n_boot > 0:
					sig = np.empty((trend.shape[0],trend.shape[1]))
					for i in np.arange(0,a.shape[1]):
					   for j in np.arange(0,a.shape[2]):
						p = hypothesis_test(a[:,i,j],b[:,i,j],n_boot)
						sig[i,j] = p

				#If interested, repeat on cond days.
				if trend_on_cond_days:
					a_cond = np.ma.masked_where(cond[np.in1d(daily_months,np.array(season)) \
						& (t1)]==0,a)
					b_cond = np.ma.masked_where(cond[np.in1d(daily_months,np.array(season)) \
						& (t2)]==0,b)
					a_wf = np.ma.masked_where(wf[np.in1d(daily_months,np.array(season)) \
						& (t1)]==0,a)
					b_wf = np.ma.masked_where(wf[np.in1d(daily_months,np.array(season)) \
						& (t2)]==0,b)
					a_sf = np.ma.masked_where(sf[np.in1d(daily_months,np.array(season)) \
						& (t1)]==0,a)
					b_sf = np.ma.masked_where(sf[np.in1d(daily_months,np.array(season)) \
						& (t2)]==0,b)
					trend_cond = (b_cond.mean(axis=0) - a_cond.mean(axis=0))
					trend_wf = (b_wf.mean(axis=0) - a_wf.mean(axis=0))
					trend_sf = (b_sf.mean(axis=0) - a_sf.mean(axis=0))
					if n_boot >0:
						sig_cond = np.empty((trend_cond.shape[0],trend_cond.shape[1]))
						for i in np.arange(0,a_cond.shape[1]):
						   for j in np.arange(0,a_cond.shape[2]):
							p = hypothesis_test(a_cond[:,i,j].data,b_cond[:,i,j].data,\
								n_boot)
							sig_cond[i,j] = p
						sig_wf = np.empty((trend_wf.shape[0],trend_wf.shape[1]))
						for i in np.arange(0,a_wf.shape[1]):
						   for j in np.arange(0,a_wf.shape[2]):
							p = hypothesis_test(a_wf[:,i,j].data,b_wf[:,i,j].data,\
								n_boot)
							sig_wf[i,j] = p
						sig_sf = np.empty((trend_sf.shape[0],trend_sf.shape[1]))
						for i in np.arange(0,a_sf.shape[1]):
						   for j in np.arange(0,a_sf.shape[2]):
							p = hypothesis_test(a_sf[:,i,j].data,b_sf[:,i,j].data,\
								n_boot)
							sig_sf[i,j] = p
				x,y=np.meshgrid(lon,lat)
				plt.figure()
				m.drawcoastlines()
				m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
						labels=[True,False,False,True])
				m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
						labels=[True,False,True,False])
				try:
					m.contourf(x,y,trend,cmap=cm.RdBu_r,extend="both",levels=trend_levels[v])
				except:
					m.contourf(x,y,trend,cmap=cm.RdBu_r,extend="both")
				if n_boot >0:
					plt.plot(x[np.where(sig<=0.05)],y[np.where(sig<=0.05)],"ko")
				else:
					add_towns(m)
				plt.colorbar()
				plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/trends/contour_"+\
					model+"_"+var_list[v]+"_"+str(season[0])+"_"+str(season[-1])+\
					"_"+str(year_range[0])+"_"+str(year_range[1])+".png",bbox_inches="tight")

				#If interested, plot for cond days
				if trend_on_cond_days:
					#COND days
					plt.figure()
					m.drawcoastlines()
					m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
							labels=[True,False,False,True])
					m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
							labels=[True,False,True,False])
					try:
						m.contourf(x,y,trend_cond,cmap=cm.RdBu_r,extend="both",\
							levels=trend_levels[v])
					except:
						m.contourf(x,y,trend_cond,cmap=cm.RdBu_r,extend="both")
					if n_boot >0:
						plt.plot(x[np.where(sig_cond<=0.05)],y[np.where(sig_cond<=0.05)],"ko")
					else:
						add_towns(m)
					plt.colorbar()
					plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/trends/contour_"+\
						model+"_"+var_list[v]+"_cond_days_"+str(season[0])+"_"+\
						str(season[-1])+"_"+str(year_range[0])+"_"+str(year_range[1])+\
						".png",bbox_inches="tight")
					#MF days
					plt.figure()
					m.drawcoastlines()
					m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
							labels=[True,False,False,True])
					m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
							labels=[True,False,True,False])
					try:
						m.contourf(x,y,trend_wf,cmap=cm.RdBu_r,extend="both",\
							levels=trend_levels[v])
					except:
						m.contourf(x,y,trend_wf,cmap=cm.RdBu_r,extend="both")
					if n_boot >0:
						plt.plot(x[np.where(sig_wf<=0.05)],y[np.where(sig_wf<=0.05)],"ko")
					else:
						add_towns(m)
					plt.colorbar()
					plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/trends/contour_"+\
						model+"_"+var_list[v]+"_wf_days_"+str(season[0])+"_"+\
						str(season[-1])+"_"+str(year_range[0])+"_"+str(year_range[1])+\
						".png",bbox_inches="tight")
					#SF days
					plt.figure()
					m.drawcoastlines()
					m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
							labels=[True,False,False,True])
					m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
							labels=[True,False,True,False])
					try:
						m.contourf(x,y,trend_sf,cmap=cm.RdBu_r,extend="both",\
							levels=trend_levels[v])
					except:
						m.contourf(x,y,trend_sf,cmap=cm.RdBu_r,extend="both")
					if n_boot >0:
						plt.plot(x[np.where(sig_sf<=0.05)],y[np.where(sig_sf<=0.05)],"ko")
					else:
						add_towns(m)
					plt.colorbar()
					plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/trends/contour_"+\
						model+"_"+var_list[v]+"_sf_days_"+str(season[0])+"_"+\
						str(season[-1])+"_"+str(year_range[0])+"_"+str(year_range[1])+\
						".png",bbox_inches="tight")

			   else:
				dmax_season1 = dmax[np.in1d(daily_months,np.array(season)) & (t1)]
				dmax_season2 = dmax[np.in1d(daily_months,np.array(season)) & (t2)]
				a = dmax_season1>=threshold[v]
				b = dmax_season2>=threshold[v]
				trend = (np.sum(b,axis=0) - np.sum(a,axis=0)) / \
						np.nansum(a,axis=0).astype(float) * 100
				#Fix "divide by zero" values to a really large %
				trend[(np.nansum(a,axis=0)==0)&(np.nansum(b,axis=0)>0)] = 1000
				if n_boot > 0:
					sig = np.empty((trend.shape[0],trend.shape[1]))
					for i in np.arange(0,a.shape[1]):
					   for j in np.arange(0,a.shape[2]):
						p = hypothesis_test(a[:,i,j],b[:,i,j],10000)
						sig[i,j] = p
				x,y=np.meshgrid(lon,lat)
				plt.figure()
				m.drawcoastlines()
				m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
						labels=[True,False,False,True])
				m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
						labels=[True,False,True,False])
				m.contourf(x,y,trend,cmap=cm.RdBu_r,levels=trend_levels,extend="both")
				if n_boot > 0:
					plt.plot(x[np.where(sig<=0.05)],y[np.where(sig<=0.05)],"ko")
				else:
					add_towns(m)
				plt.colorbar()
				plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/trends/contour_"+\
					model+"_"+var_list[v]+"_"+str(season[0])+"_"+str(season[-1])+"_"+str(threshold[v])\
					+"_"+str(year_range[0])+"_"+str(year_range[1])+".png",bbox_inches="tight")

		#PLOT CLIM IND CORRELATIONS
		#BACK OUTSIDE OF THE SEASONS LOOP
		if plot_corr:
		    nino34 = read_clim_ind("nino34")
		    dmi = read_clim_ind("dmi")
		    sam = read_clim_ind("sam")
	
		    if var_list[v] == "cond":
			plot_corr_func(m,lon,lat,model,nino34,dmi,sam,dmax,daily_years,daily_months,"cond",False,\
				year_range,n_boot)	
			plot_corr_func(m,lon,lat,model,nino34,dmi,sam,sf,daily_years,daily_months,"sf",False,\
				year_range,n_boot)	
			plot_corr_func(m,lon,lat,model,nino34,dmi,sam,wf,daily_years,daily_months,"wf",False,\
				year_range,n_boot)	
		    else:
			plot_corr_func(m,lon,lat,model,nino34,dmi,sam,dmax,daily_years,daily_months,var_list[v],\
				threshold[v],year_range,n_boot)	

def plot_corr_func(m,lon,lat,model,nino34,dmi,sam,dmax,daily_years,daily_months,var_name,threshold,year_range,n_boot):
		corr_seasons = [[2,3,4],[5,6,7],[8,9,10],[11,12,1],np.arange(1,13,1)]
		names = nino34.columns
		years = nino34.index
		monthly_ts = np.empty((len(names),len(years),lat.shape[0],lon.shape[0]))
		nino34_p = np.empty((len(names),lat.shape[0],lon.shape[0]))
		sam_p = np.empty((len(names),lat.shape[0],lon.shape[0]))
		dmi_p = np.empty((len(names),lat.shape[0],lon.shape[0]))
		years_p = np.empty((len(names),lat.shape[0],lon.shape[0]))
		nino34_corr = np.empty((len(names),lat.shape[0],lon.shape[0]))
		sam_corr = np.empty((len(names),lat.shape[0],lon.shape[0]))
		dmi_corr = np.empty((len(names),lat.shape[0],lon.shape[0]))
		years_corr = np.empty((len(names),lat.shape[0],lon.shape[0]))
		for s in np.arange(0,len(names)):
		    for y in np.arange(0,len(years)):
			#If the variable/parameter being considered is using a threshold, then find a monthly time
			#series of threshold exceedence
			if threshold != False:
				if s == 3:	#IF NDJ
					cond = ((daily_years==years[y]) & (daily_months==corr_seasons[s][0])) \
						| ((daily_years==years[y]) & (daily_months==corr_seasons[s][1])) \
						| ((daily_years==years[y]+1) & (daily_months==corr_seasons[s][2]))
					monthly_ts[s,y] = np.sum(dmax[cond] >= threshold,axis=0)
				else:
					cond = (daily_years==years[y]) & (np.in1d(daily_months,corr_seasons[s]))
					monthly_ts[s,y] = np.sum(dmax[cond] >= threshold,axis=0)
			#If variable is "cond", then we do not need to find threshold exceedence, as it is already
			# in the form of binary/boolean condition
			else:
				if s == 3:	#IF NDJ
					cond = ((daily_years==years[y]) & (daily_months==corr_seasons[s][0])) \
						| ((daily_years==years[y]) & (daily_months==corr_seasons[s][1])) \
						| ((daily_years==years[y]+1) & (daily_months==corr_seasons[s][2]))
					monthly_ts[s,y] = np.sum(dmax[cond],axis=0)
				else:
					cond = (daily_years==years[y]) & (np.in1d(daily_months,corr_seasons[s]))
					monthly_ts[s,y] = np.sum(dmax[cond],axis=0)

		    #Calculate correlations
		    for i in np.arange(0,len(lat)):
			for j in np.arange(0,len(lon)):
				c,p = rho(nino34[names[s]],monthly_ts[s,:,i,j])
				nino34_corr[s,i,j] = c
				nino34_p[s,i,j] = p

				c,p = rho(dmi[names[s]],monthly_ts[s,:,i,j])
				dmi_corr[s,i,j] = c
				dmi_p[s,i,j] = p

				c,p = rho(sam[names[s]],monthly_ts[s,:,i,j])
				sam_corr[s,i,j] = c
				sam_p[s,i,j] = p

				c,p = rho(np.arange(0,nino34.shape[0]),monthly_ts[s,:,i,j])
				years_corr[s,i,j] = c
				years_p[s,i,j] = p
		    #PLOT
		    #NINO 3.4
		    plt.figure()
		    m.drawcoastlines()
		    m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
				labels=[True,False,False,True])
		    m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
				labels=[True,False,True,False])
		    x,y=np.meshgrid(lon,lat)
		    m.contourf(x,y,nino34_corr[s],cmap=cm.RdBu_r,levels=np.linspace(-0.5,0.5,11)\
			,extend="both")
		    plt.plot(x[np.where(nino34_p[s]<=0.05)],y[np.where(nino34_p[s]<=0.05)],"ko")
		    plt.colorbar()
		    plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/corr/nino34_"+\
			model+"_"+var_name+"_"+names[s]+"_"+str(threshold)\
			+"_"+str(year_range[0])+"_"+str(year_range[1])+".png",bbox_inches="tight")
		    plt.close()
		    #DMI
		    plt.figure()
		    m.drawcoastlines()
		    m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
				labels=[True,False,False,True])
		    m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
				labels=[True,False,True,False])
		    x,y=np.meshgrid(lon,lat)
		    m.contourf(x,y,dmi_corr[s],cmap=cm.RdBu_r,levels=np.linspace(-0.5,0.5,11)\
			,extend="both")
		    plt.plot(x[np.where(dmi_p[s]<=0.05)],y[np.where(dmi_p[s]<=0.05)],"ko")
		    plt.colorbar()
		    plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/corr/dmi_"+\
			model+"_"+var_name+"_"+names[s]+"_"+str(threshold)\
			+"_"+str(year_range[0])+"_"+str(year_range[1])+".png",bbox_inches="tight")
		    plt.close()
		    #NINO 3.4
		    plt.figure()
		    m.drawcoastlines()
		    m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
				labels=[True,False,False,True])
		    m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
				labels=[True,False,True,False])
		    x,y=np.meshgrid(lon,lat)
		    m.contourf(x,y,sam_corr[s],cmap=cm.RdBu_r,levels=np.linspace(-0.5,0.5,11)\
			,extend="both")
		    plt.plot(x[np.where(sam_p[s]<=0.05)],y[np.where(sam_p[s]<=0.05)],"ko")
		    plt.colorbar()
		    plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/corr/sam_"+\
			model+"_"+var_name+"_"+names[s]+"_"+str(threshold)\
			+"_"+str(year_range[0])+"_"+str(year_range[1])+".png",bbox_inches="tight")
		    plt.close()
		    #YEARS (trend)
		    plt.figure()
		    m.drawcoastlines()
		    m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
				labels=[True,False,False,True])
		    m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
				labels=[True,False,True,False])
		    x,y=np.meshgrid(lon,lat)
		    m.contourf(x,y,years_corr[s],cmap=cm.RdBu_r,levels=np.linspace(-0.5,0.5,11)\
			,extend="both")
		    plt.plot(x[np.where(years_p[s]<=0.05)],y[np.where(years_p[s]<=0.05)],"ko")
		    plt.colorbar()
		    plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/corr/years_"+\
			model+"_"+var_name+"_"+names[s]+"_"+str(threshold)\
			+"_"+str(year_range[0])+"_"+str(year_range[1])+".png",bbox_inches="tight")
		    plt.close()



def diurnal_clim(domain,model,year_range,var,threshold=0):

	#Import a netcdf dataset and plot the mean time for which a threshold is exceeded

	print("INFO: Loading data for "+model+" on domain "+domain+" between "+str(year_range[0])+\
		" and "+str(year_range[1]))
	#Create filenames in year range
	fnames = list()
	for y in np.arange(year_range[0],year_range[1]+1):
		fnames.extend(glob.glob("/g/data/eg3/ab4502/ExtremeWind/"+domain+"/"+model+"/"+model+\
			"_"+str(y)+"*.nc"))
	fnames.sort()
	f = nc.MFDataset(fnames)
	lon = f.variables["lon"][:]
	lat = f.variables["lat"][:]
	vars = np.array([str(f.variables.items()[i][0]) for i in np.arange(0,\
		len(f.variables.items()))])
	vars = vars[~(vars=="time") & ~(vars=="lat") & ~(vars=="lon")]
	time = nc.num2date(f.variables["time"][:],f.variables["time"].units)
	years = np.array([t.year for t in time])
	months = np.array([t.month for t in time])
	days = np.array([t.day for t in time])
	hours = np.array([t.hour for t in time])
	y1 = str(years.min())
	y2 = str(years.max())
	warm_inds = np.array([m in np.array([10,11,12,1,2,3]) for m in months])
	cool_inds = ~warm_inds
	hours_warm = np.array([t.hour for t in time[warm_inds]])
	hours_cool = np.array([t.hour for t in time[cool_inds]])

	data = f.variables[var][:]

	hours_clim = np.empty((lat.shape[0],lon.shape[0]))
	hours_warm_clim = np.empty((lat.shape[0],lon.shape[0]))
	hours_cool_clim = np.empty((lat.shape[0],lon.shape[0]))
	for i in np.arange(lat.shape[0]):
	    print(i)
	    for j in np.arange(lon.shape[0]):
		hours_clim[i,j] = np.mean(hours[np.where(data[:,i,j]>=threshold)])
		hours_warm_clim[i,j] = np.mean(hours_warm[np.where(data[warm_inds,i,j]>=threshold)])
		hours_cool_clim[i,j] = np.mean(hours_cool[np.where(data[cool_inds,i,j]>=threshold)])

	plot_diurnal_clim(hours_clim,lon,lat,model,var,threshold,"all")
	plot_diurnal_clim(hours_warm_clim,lon,lat,model,var,threshold,"warm")
	plot_diurnal_clim(hours_cool_clim,lon,lat,model,var,threshold,"cold")

def plot_diurnal_clim(hours_clim,lon,lat,model,var,threshold,outname):
	m = Basemap(llcrnrlon = lon.min(), llcrnrlat = lat.min(), urcrnrlon = lon.max(), \
				urcrnrlat = lat.max(), projection="cyl", resolution = "l")
	lon,lat = np.meshgrid(lon,lat)
	fig = plt.figure()
	m.drawcoastlines()
	m.contourf(lon,lat,hours_clim,latlon=True,levels = np.arange(0,27,3))
	plt.colorbar()
	fig.savefig("/home/548/ab4502/working/ExtremeWind/figs/clim/"+model+\
		"_"+var+"_hours_"+str(threshold)+"_"+outname+".png")
	plt.close()

def wind_gust_filter(array):

	#Remove points over 60 m/s. Also remove points over 40 m/s, if there is no other gust over
	# 30 m/s for the day

	array[array>=60] = np.nan
	gust_spikes_ind = np.where(array>40)
	for j in np.arange(0,len(gust_spikes_ind[0])):
	    if np.sort(array[:,gust_spikes_ind[1][j],gust_spikes_ind[2][j]])[-2]<30:
		array[gust_spikes_ind[0][j],gust_spikes_ind[1][j],\
			gust_spikes_ind[2][j]] = np.nan
	return(array)

def plot_clim(f,m,lat,lon,mean,var,model,domain,year_range,season,levels=False,threshold=""):

	plt.figure()
	#if levels==False:
	#	cmap,levels,extreme_levels,cb_lab,range,log_plot,thresholds = contour_properties(var)	
	#else:
	cmap,temp,extreme_levels,cb_lab,range,log_plot,thresholds = contour_properties(var)	
	m.drawcoastlines()
	m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
			labels=[True,False,False,True])
	m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
			labels=[True,False,True,False])
	x,y = np.meshgrid(lon,lat)
	try:
		m.contourf(x,y,mean,latlon=True,levels=levels,cmap=cmap,extend="max")
	except:
		m.contourf(x,y,mean,latlon=True,cmap=cmap,extend="both")
	cb=plt.colorbar()
	#cb.set_label(f.variables[var].units)
	#if model == "barra_ad":
	#	terrain = nc.Dataset("/g/data/ma05/BARRA_AD/v1/static/topog-an-slv-PT0H-BARRA_AD-v1.nc").\
	#			variables["topog"][:]
	#	terrain_lon,terrain_lat = get_barra_ad_lat_lon()
	#	terrain_lon,terrain_lat = np.meshgrid(terrain_lon,terrain_lat)
	#if model == "barra_r_fc":
	terrain = nc.Dataset("/g/data/ma05/BARRA_R/v1/static/topog-an-slv-PT0H-BARRA_R-v1.nc").\
			variables["topog"][:]
	terrain_lon,terrain_lat = get_barra_r_lat_lon()
	terrain_lon,terrain_lat = np.meshgrid(terrain_lon,terrain_lat)
	#elif model == "erai":
		#terrain = np.squeeze(nc.Dataset("/short/eg3/ab4502/erai_sfc_geopt.nc").\
		#		variables["z"][:] / 9.8)
		#terrain_lon,terrain_lat = get_lat_lon()
		#terrain_lon,terrain_lat = np.meshgrid(terrain_lon,terrain_lat)

	m.contour(terrain_lon,terrain_lat,terrain,latlon=True,levels=[250,500,750],colors="grey")
	add_towns(m)
	plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/clim/"+model+"_"+var+\
		"_"+str(season[0])+"_"+str(season[-1])+"_"+str(threshold)+"_"+str(year_range[0])+"_"+\
		str(year_range[-1])+".png",bbox_inches="tight")
	plt.close()

def add_towns(m):

	#Add towns to Basemap contour
	names = ["Adel","Woomera","Pt Augusta","Mt Gambier"]
	#,"Clare","Coober Pedy AP","Renmark","Munkora"]
	lons = [138.5196,136.8054,137.7169,140.7739]
	#,138.5933,134.7222,140.6766,140.3273]
	lats = [-34.9524,-31.1558,-32.5073,-37.7473]
	#,-33.8226,-29.0347,-34.1983,-36.1058]
	for i in np.arange(0,len(names)):
		x,y = m(lons[i],lats[i])
		plt.annotate(names[i],xy=(x,y+.12),color="k",size="small",ha="center")
		plt.plot(x,y,"ko")
	
def spatial_trends(var,arr1, arr2, domain, lon, lat, year_range):

	#Take a rectangular area given by domain ( = [start_lon,start_lat,end_lon,end_lat])
	#Calculate the trend in environment days from 1979-2017, by the difference in the 
	#	first (arr1) and second half (arr2) of the period
	#Convert trend to days/decade
	#Save trend as csv

	outside_bounds = (lon < domain[0]) | (lat < domain[1]) | (lon > domain[2]) | (lat > domain[3])

	#Take the change by subtraction, then take mean
	trend = np.ma.masked_where(outside_bounds,(arr2.sum(axis=0) - arr1.sum(axis=0))).mean()

	#Now, divide each result by the amount of decades
	trend = trend / float((year_range[1] - year_range[0] + 1) / 10.)

	#What was the mean number of days in the first half of the period?
	days1 = np.ma.masked_where(outside_bounds,arr1.sum(axis=0)).mean()
	days2 = np.ma.masked_where(outside_bounds,arr2.sum(axis=0)).mean()

	#Save as csv
	df = pd.DataFrame({"Trend":trend,"Days1":days1,"Days2":days2},index=["Value"])
	df.to_csv("/home/548/ab4502/working/ExtremeWind/figs/trends/erai_spatial_"+var+".csv")

	#Take the change by asking for each timestep, is there an event in the region
	events1 = np.array([np.ma.masked_where(outside_bounds,arr1[t]).max() for t in np.arange(arr1.shape[0])])
	events2 = np.array([np.ma.masked_where(outside_bounds,arr2[t]).max() for t in np.arange(arr2.shape[0])])
	trend = (np.sum(events2) - np.sum(events1)) / float((year_range[1] - year_range[0] + 1) / 10.)
	days1 = np.sum(events1)
	days2 = np.sum(events2)
	df = pd.DataFrame({"Trend":trend,"Days1":days1,"Days2":days2},index=["Value"])
	df.to_csv("/home/548/ab4502/working/ExtremeWind/figs/trends/erai_spatial_events_"+var+".csv")


if __name__ == "__main__":
	#clim("sa_small","erai",[1979,2017])
	#clim("sa_small","erai_fc",[1979,2017])
	#clim("sa_small","erai",[2010,2015])
	#clim("sa_small","erai_fc",[2010,2015])
	#clim("sa_small","barra",[2010,2015])
	#diurnal_clim("sa_small","barra_r_fc",[2003,2016],"max_wg10",threshold=30)
	daily_max_clim("sa_small","erai",[1979,2017],\
		var_list=["cond"],\
		levels=False,\
		plot_trends=True, n_boot = 0, plot_corr = False)

	#FIGURE 14:
	#THRESHOLD 1
	#daily_max_clim("sa_small","erai",[1979,2017],threshold=[127,22790,0.027,0.025,23.83],var_list=[\
			#"ml_cape","mlcape*s06","ship","scp","s06"],levels=[np.arange(0,55,5),np.arange(0,33,3),\
			#np.arange(0,55,5),np.arange(0,55,5),np.linspace(0,80,11)],plot_trends=True,\
			#seasons = [np.arange(1,13,1),[11,12,1],[2,3,4],[5,6,7],[8,9,10]],\
			#trend_levels=np.linspace(-50,50,11))
	#S06
	#daily_max_clim("sa_small","erai",[1979,2017],threshold=[23.83],var_list=[\
	#		"s06"],levels=[np.linspace(0,80,11)],plot_trends=True,\
	#		seasons = [np.arange(1,13,1),[11,12,1],[2,3,4],[5,6,7],[8,9,10]],\
	#		trend_levels=np.linspace(-50,50,11))
	#THRESHOLD 2
	#daily_max_clim("sa_small","erai",[1979,2017],threshold=[68000,1,1],var_list=[\
			#"mlcape*s06","ship","scp"],levels=[np.arange(0,11,1),\
			#np.linspace(0,6,11),np.linspace(0,2,11)],plot_trends=True,\
			#seasons = [np.arange(1,13,1),[11,12,1],[2,3,4],[5,6,7],[8,9,10]],\
			#trend_levels=np.linspace(-50,50,11))
	#FIGURE 7:
	#daily_max_clim("sa_small","erai_fc",[1979,2017],threshold=[21.5],var_list=["wg10"],\
	#		levels=[np.arange(0,2.2,.2)],plot_trends=True,plot_corr=True,\
	#		trend_levels=np.arange(-175,175,25),seasons = [np.arange(1,13,1),[11,12,1],[2,3,4],\
	#		[5,6,7],[8,9,10]])
	#99.6 percentile BARRA-R wind gust: 25.25. ERA-Interim: 21.5

	#FIGURE 20:
	#daily_max_clim("sa_small","erai",[2003,2016],threshold=[6029.981,0.429],var_list=["cape*s06",\
	#		"mlm*dcape*cs6"],levels=[np.arange(0,55,5),np.arange(0,55,5)],\
	#		plot_trends=False,plot_corr=False)
	#daily_max_clim("sa_small","barra",[2003,2016],threshold=[6029.981,0.429],var_list=["cape*s06",\
	#		"mlm*dcape*cs6"],levels=[np.arange(0,55,5),np.arange(0,55,5)],\
	#		plot_trends=False,plot_corr=False)
	#Figure 20/22/23
	#daily_max_clim("sa_small","erai",[1979,2017],threshold=[6029.981,0.429,120],\
	#		var_list=["cape*s06","mlm*dcape*cs6","ml_cape"],\
	#		levels=[np.arange(0,55,5),np.arange(0,55,5),np.arange(0,55,5)],\
	#		plot_trends=True,plot_corr=True)
	#FIGURE 20:
	#daily_max_clim("sa_small","erai",[2003,2016],threshold=[0.028],var_list=["dcp"],\
	#	levels=[np.arange(0,55,5)],plot_trends=False,plot_corr=False)
	#daily_max_clim("sa_small","barra",[2003,2016],threshold=[0.028],var_list=["dcp"],\
	#	levels=[np.arange(0,55,5)],plot_trends=False,plot_corr=False)
	#Figure 20/22/23
	#daily_max_clim("sa_small","erai",[1979,2017],threshold=[0.028],\
	#	var_list=["dcp"],\
	#	levels=[np.arange(0,55,5)],\
	#	plot_trends=True,plot_corr=True,n_boot=1000)

	#Figure 6
#	daily_max_clim("sa_small","erai_fc",[2003,2016],threshold=[21.5],vars=["wg10"],\
#		levels=[np.linspace(0,5,11)])
#	daily_max_clim("sa_small","barra_r_fc",[2003,2016],threshold=[25.25],vars=["max_wg10"],\
#		levels=[np.linspace(0,5,11)])
#	daily_max_clim("sa_small","erai_fc",[1979,2017],threshold=[21.5],vars=["wg10"],\
#		levels=[np.linspace(0,2,11)],seasons=[[11,12,1],[2,3,4],[5,6,7],[8,9,10]])
#	daily_max_clim("sa_small","erai_fc",[1979,2017],threshold=[21.5],vars=["wg10"],\
#		levels=[np.linspace(0,5,11)])

	#DAILY MEAN CLIM
	#clim("sa_small","erai",[2003,2016],["s06","dcape","ml_cape","dlm"])

	#Figure 20/21/22/23
	#daily_max_clim("sa_small","erai",[2003,2016],var_list=["cond"],plot_trends=False,plot_corr=False)
	#daily_max_clim("sa_small","barra",[2003,2016],var_list=["cond"],plot_trends=False,plot_corr=False)
	#daily_max_clim("sa_small","erai",[1979,2017],var_list=["cond"],plot_trends=True,plot_corr=True)

	#Ingredients
	#daily_max_clim("sa_small","erai",[1979,2017],var_list=["tos"],\
	#		plot_trends=True,trend_levels=[np.linspace(-1.5,1.5,11)],n_boot=0,\
	#		trend_on_cond_days=True)
	#daily_max_clim("sa_small","erai",[1979,2017],var_list=["ta2d","tas","tos"],\
	#		plot_trends=True,\
	#		trend_levels=[np.linspace(-1.5,1.5,11),np.linspace(-1.5,1.5,11),np.linspace(-2,2,11)]\
	#		,n_boot=1000,trend_on_cond_days=True,\
	#		seasons=[np.arange(1,13,1),[11,12,1],[2,3,4],[5,6,7],[8,9,10]])