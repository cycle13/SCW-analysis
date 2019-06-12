from barra_read import date_seq
import numpy as np
import datetime as dt
import glob
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import matplotlib.cm as cm
import netCDF4 as nc
import matplotlib.animation as animation
import os
from event_analysis import *
from scipy.interpolate import griddata
from scipy.stats import gaussian_kde
from matplotlib.colors import LogNorm

def plot_netcdf(domain,fname,outname,time,model,vars=False):

#Load a single netcdf file and plot time max if time is a list of [start_time,end_time]
# or else plot for a single time if time is length=1

	f = nc.Dataset(fname)
	lon = f.variables["lon"][:]
	lat = f.variables["lat"][:]
	x,y = np.meshgrid(lon,lat)
	times = f.variables["time"][:]
	times_dt = nc.num2date(times,f.variables["time"].units)

	if vars == False:
		vars = np.array([str(f.variables.items()[i][0]) for i in np.arange(0,\
		len(f.variables.items()))])
		vars = vars[~(vars=="time") & ~(vars=="lat") & ~(vars=="lon")]	
	
	m = Basemap(llcrnrlon = domain[2], llcrnrlat = domain[0], urcrnrlon = domain[3], \
				urcrnrlat = domain[1], projection="cyl", resolution = "i")
	for param in vars:
		if len(time)==2:
			values = np.nanmax(f.variables[param][(times_dt>=time[0]) & \
				(times_dt<=time[-1])],axis=0)
			plt.title(str(time[0]) + "-" + str(time[-1]))
		else:
			if param == "mlcape*s06":
				values = np.squeeze(f.variables["ml_cape"][times_dt == time] * \
					np.power(f.variables["s06"][times_dt == time],1.67))
			elif param == "cond":
				mlcape = np.squeeze(f.variables["ml_cape"][times_dt == time])
				dcape = np.squeeze(f.variables["dcape"][times_dt == time])
				s06 = np.squeeze(f.variables["s06"][times_dt == time])
				mlm = np.squeeze(f.variables["mlm"][times_dt == time])
				sf = ((s06>=30) & (dcape<500) & (mlm>=26) ) 
				wf = ((mlcape>120) & (dcape>350) & (mlm<26) ) 
				values = sf | wf 
				values = values * 1.0; sf = sf * 1.0; wf = wf * 1.0
				values_disc = np.zeros(values.shape)
				#Separate conditions 1 and 2 (strong forcing and weak forcing)
				#Make in to an array with 1's for SF, 2's for WF and 3's for both types
				values_disc[sf==1] = 1
				values_disc[wf==1] = 2
			else:
				values = np.squeeze(f.variables[param][times_dt == time])
			plt.title(str(time[0]))

		print(param)
		[cmap,mean_levels,levels,cb_lab,range,log_plot,threshold] = contour_properties(param)

		plt.figure()

		m.drawcoastlines()
		if (domain[0]==-38) & (domain[1]==-26):
			m.drawmeridians([134,137,140],\
					labels=[True,False,False,True],fontsize="xx-large")
			m.drawparallels([-36,-34,-32,-30,-28],\
					labels=[True,False,True,False],fontsize="xx-large")
		else:
			m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
					labels=[True,False,False,True])
			m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
					labels=[True,False,True,False])
		if param == "cond":
			m.pcolor(x,y,values,latlon=True,cmap=plt.get_cmap("Reds",2))
		else:
			m.contourf(x,y,values,latlon=True,cmap=cmap,levels=levels,extend="max")
		cb = plt.colorbar()
		cb.set_label(cb_lab,fontsize="xx-large")
		cb.ax.tick_params(labelsize="xx-large")
		if param == "cond":
			cb.set_ticks([0,1])
		m.contour(x,y,values,latlon=True,colors="grey",levels=threshold)
		if (outname == "system_black_2016092806"):
			tx = (138.5159,138.3505,138.0996)
			ty = (-33.7804,-32.8809,-32.6487)
			m.plot(tx,ty,color="k",linestyle="none",marker="^",markersize=10)
		#plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/"+model+"/"+outname+\
		#	"_"+param+".png",bbox_inches="tight")
		plt.savefig("/short/eg3/ab4502/figs/ExtremeWind/"+model+"_"+outname+\
			"_"+param+".tiff",bbox_inches="tight")
		plt.close()
		#IF COND, ALSO DRAW COND TYPES
		if param == "cond":
			plt.figure()
			m.drawcoastlines()
			if (domain[0]==-38) & (domain[1]==-26):
				m.drawmeridians([134,137,140],\
						labels=[True,False,False,True],fontsize="xx-large")
				m.drawparallels([-36,-34,-32,-30,-28],\
						labels=[True,False,True,False],fontsize="xx-large")
			else:
				m.drawmeridians(np.arange(np.floor(lon.min()),np.floor(lon.max()),3),\
						labels=[True,False,False,True])
				m.drawparallels(np.arange(np.floor(lat.min()),np.floor(lat.max()),3),\
						labels=[True,False,True,False])
			m.pcolor(x,y,values_disc,latlon=True,cmap=plt.get_cmap("Accent_r",3),vmin=0,vmax=2)
			cb = plt.colorbar()
			cb.set_label("Forcing type",fontsize="xx-large")
			cb.set_ticks([0,1,2,3])
			cb.set_ticklabels(["None","SF","MF","Both"])
			cb.ax.tick_params(labelsize="xx-large")
			plt.savefig("/short/eg3/ab4502/figs/ExtremeWind/"+model+"_"+outname+\
				"_"+"forcing_types"+".tiff",bbox_inches="tight")
			#plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/"+model+"/"+outname+\
			#	"_"+"forcing_types"+".png",bbox_inches="tight")
			plt.close()

def plot_netcdf_animate(fname,param,outname,domain):

#Load a single netcdf file and plot the time animation

	global values, times_str, x, y, levels, cmap, cb_lab, m

	Writer = animation.writers['ffmpeg']
	writer = Writer(fps=15, bitrate=1800)

	f = nc.Dataset(fname)
	values = f.variables[param][:]
	lon = f.variables["lon"][:]
	lat = f.variables["lat"][:]
	x,y = np.meshgrid(lon,lat)
	times = f.variables["time"][:]
	times_dt = nc.num2date(times,f.variables["time"].units)
	times_str = [dt.datetime.strftime(t,"%Y-%m-%d %H:%M") for t in times_dt]

	[cmap,levels,cb_lab] = contour_properties(param)

	m = Basemap(llcrnrlon = domain[2], llcrnrlat = domain[0], urcrnrlon = domain[3], \
				urcrnrlat = domain[1], projection="cyl", resolution = "l")
	
	fig = plt.figure()
	m.contourf(x,y,np.zeros(x.shape),latlon=True,levels=levels,cmap=cmap,extend="both")
	m.drawcoastlines()
	m.drawmeridians(np.arange(domain[2],domain[3],5),\
			labels=[True,False,False,True])
	m.drawparallels(np.arange(domain[0],domain[1],5),\
			labels=[True,False,True,False])
	cb = plt.colorbar()
	cb.set_label(cb_lab)
	anim = animation.FuncAnimation(fig, animate, frames=values.shape[0],interval=500)
	anim.save("/home/548/ab4502/working/ExtremeWind/figs/mean/"+outname+".mp4",\
			writer=writer)
	plt.show()

def animate(i):
	z = values[i]
	m.drawcoastlines()
	m.drawmeridians(np.arange(domain[2],domain[3],5),\
			labels=[True,False,False,True])
	m.drawparallels(np.arange(domain[0],domain[1],5),\
			labels=[True,False,True,False])
	im = m.contourf(x,y,values[i],latlon=True,levels=levels,cmap=cmap,extend="both")
	plt.title(times_str[i] + " UTC")
	return im
	
def contour_properties(param):
	threshold = [1]
	if param in ["mu_cape","cape","cape700"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,2000,11)
		extreme_levels = np.linspace(0,2000,11)
		cb_lab = "J.kg$^{-1}$"
		range = [0,4000]
		log_plot = True
	if param in ["dlm*dcape*cs6","mlm*dcape*cs6"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,4,11)
		extreme_levels = np.linspace(0,40,11)
		cb_lab = ""
		range = [0,40]
		log_plot = True
		threshold = [0.669]
	elif param == "ml_cape":
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,60,11)
		extreme_levels = np.linspace(0,2000,11)
		cb_lab = "J.kg$^{-1}$"
		threshold = [127]
		range = [0,4000]
		log_plot = True
	elif param == "mu_cin":
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,200,11)
		extreme_levels = np.linspace(0,500,11)
		cb_lab = "J/Kg"
		range = [0,500]
		log_plot = True
	elif param == "ml_cin":
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,200,11)
		extreme_levels = np.linspace(0,400,11)
		cb_lab = "J/Kg"
		range = [0,600]
		log_plot = False
	elif param in ["s06","ssfc6"]:
		cmap = cm.Reds
		mean_levels = np.linspace(14,18,17)
		extreme_levels = np.linspace(0,50,11)
		cb_lab = "m.s$^{-1}$"
		threshold = [23.83]
		range = [0,60]
		log_plot = False
	elif param in ["ssfc3"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,30,7)
		extreme_levels = np.linspace(0,40,11)
		cb_lab = "m/s"
		range = [0,30]
		log_plot = False
	elif param in ["ssfc850"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,20,7)
		extreme_levels = np.linspace(0,30,11)
		cb_lab = "m/s"
		range = [0,25]
		log_plot = False
	elif param in ["ssfc500","ssfc1"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,20,7)
		extreme_levels = np.linspace(0,30,11)
		cb_lab = "m/s"
		range = [0,20]
		log_plot = False
	elif param in ["dcp"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,0.5,11)
		extreme_levels = np.linspace(0,4,11)
		cb_lab = "DCP"
		range = [0,3]
		threshold = [0.028,1]
		log_plot = True
	elif param in ["scp"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,0.5,11)
		extreme_levels = np.linspace(0,4,11)
		cb_lab = ""
		range = [0,3]
		threshold = [0.025,1]
		log_plot = True
	elif param in ["stp","ship","non_sc_stp"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,0.5,11)
		extreme_levels = np.linspace(0,2.5,11)
		cb_lab = ""
		threshold = [0.027,1]
		range = [0,3]
		log_plot = True
	elif param in ["mmp"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,1,11)
		extreme_levels = np.linspace(0,1,11)
		cb_lab = ""
		range = [0,1]
		log_plot = True
	elif param in ["srh01","srh03","srh06"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,200,11)
		extreme_levels = np.linspace(0,600,11)
		cb_lab = "m^2/s^2"
		range = [0,400]
		log_plot = True
	elif param == "crt":
		cmap = cm.YlGnBu
		mean_levels = [60,120]
		extreme_levels = [60,120]
		cb_lab = "degrees"
		range = [0,180]
		log_plot = False
	elif param in ["relhum850-500","relhum1000-700","hur850","hur700"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,100,11)
		extreme_levels = np.linspace(0,100,11)
		cb_lab = "%"
		range = [0,100]
		log_plot = False
	elif param == "vo":
		cmap = cm.RdBu_r
		mean_levels = np.linspace(-8e-5,8e-5,17)
		extreme_levels = np.linspace(-8e-5,8e-5,17)
		cb_lab = "s^-1"
		range = [-8e-5,-8e-5]
		log_plot = False
	elif param == "lr1000":
		cmap = cm.Blues
		mean_levels = np.linspace(2,12,11)
		extreme_levels = np.linspace(2,12,11)
		cb_lab = "deg/km"
		range = [0,12]
		log_plot = False
	elif param == "lcl":
		cmap = cm.YlGnBu_r
		mean_levels = np.linspace(0,8000,9)
		extreme_levels = np.linspace(0,8000,9)
		cb_lab = "m"
		range = [0,8000]
		log_plot = False
	elif param in ["td800","td850","td950"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,30,9)
		extreme_levels = np.linspace(0,30,9)
		cb_lab = "deg"
		range = [0,40]
		log_plot = False
	elif param in ["cape*s06","cape*ssfc6","mlcape*s06"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,500000,11)
		extreme_levels = np.linspace(0,500000,11)
		cb_lab = ""
		range = [0,100000]
		threshold = [10344.542,68000]
		log_plot = True
	elif param in ["cape*td850"]:
		cmap = cm.YlGnBu
		mean_levels = None
		extreme_levels = None
		cb_lab = ""
		range = None
		log_plot = True
	elif param in ["dp850-500","dp1000-700","dp850","dp700"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(-10,10,11)
		extreme_levels = np.linspace(-10,10,11)
		cb_lab = "degC"
		range = [-20,20]
		log_plot = False
	elif param in ["dlm","mlm"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(5,15,11)
		extreme_levels = np.linspace(0,50,11)
		threshold = [1]
		cb_lab = "m/s"
		range = [0,50]
		log_plot = False
	elif param in ["dcape"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,400,11)
		extreme_levels = np.linspace(0,2000,11)
		threshold = [500]
		cb_lab = "J/kg"
		range = [0,2000]
		log_plot = False
	elif param in ["mfper"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,0.1,11)
		extreme_levels = np.linspace(0,1,2)
		threshold = [1]
		cb_lab = "% of WF"
		range = [0,1]
		log_plot = False
	elif param in ["cond","sf","mf"]:
		cmap = cm.Reds
		mean_levels = np.linspace(0,0.1,11)
		extreme_levels = np.linspace(0,1,2)
		threshold = [1]
		cb_lab = "CEWP"
		range = [0,1]
		log_plot = False
	elif param in ["max_wg10","wg10"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,200,11)
		extreme_levels = np.linspace(-10,10,11)
		threshold = [12.817,21.5]
		cb_lab = "no. of days"
		range = [0,30]
		log_plot = False
	elif param in ["tas","ta850","ta700","tos"]:
		cmap = cm.Reds
		mean_levels = np.linspace(285,320,5)
		extreme_levels = np.linspace(-10,10,11)
		threshold = [1]
		cb_lab = "K"
		range = [-20,20]
		log_plot = False
	elif param in ["ta2d"]:
		cmap = cm.YlGnBu
		mean_levels = np.linspace(0,200,11)
		extreme_levels = np.linspace(-10,10,11)
		threshold = [12.817,21.5]
		cb_lab = "no. of days"
		range = [-20,20]
		log_plot = False
	
	return [cmap,mean_levels,extreme_levels,cb_lab,range,log_plot,threshold]

def get_far66(df,event,param):
	#For a dataframe containing reanalysis parameters, and columns corresponding to some 
	#deinition of an "event", return the FAR for a 2/3 hit rate

	param_thresh = np.percentile(df[df[event]==1][param],33)
	df["param_thresh"] = (df[param]>=param_thresh)*1
	false_alarms = np.float(((df["param_thresh"]==1) & (df[event]==0)).sum())
	hits = np.float(((df["param_thresh"]==1) & (df[event]==1)).sum())
	correct_negatives = np.float(((df["param_thresh"]==0) & (df[event]==0)).sum())
	fa_ratio =  false_alarms / (hits+false_alarms)
	fa_rate =  false_alarms / (correct_negatives+false_alarms)
	return (fa_ratio,fa_rate,param_thresh)

def plot_diurnal_wind_distribution():
	#Plot the diurnal distributions of AWS-defined wind gust events

	#Load unsampled (half-horuly) aws data
	aws_30min = pd.read_pickle("/short/eg3/ab4502/ExtremeWind/aws/"+\
			"all_wind_gusts_sa_1985_2017.pkl").reset_index().sort_values(["date","stn_name"])
	#Change to local time
	aws_30min["date_lt"] = aws_30min.date + dt.timedelta(hours = -10.5)
	aws_30min["hour"] = [x.hour for x in aws_30min.date_lt]
	aws_30min["month"] = [x.month for x in aws_30min.date_lt]
	#Attempt to eliminate erroneous values
	inds = aws_30min[aws_30min.wind_gust>=40].index.values
	err_cnt=0
	for i in inds:
		prev = aws_30min.loc[i-1].wind_gust
		next = aws_30min.loc[i+1].wind_gust
		if (prev < 20) & (next < 20):
			aws_30min.wind_gust.iat[i] = np.nan
			err_cnt = err_cnt+1

	aws_30min_warm_inds = np.in1d(aws_30min.month,np.array([10,11,12,1,2,3]))

	#Get diurnal distribution for 30 min data
	for loc in ["Adelaide AP","Port Augusta","Woomera","Mount Gambier"]:
		aws_30min_5_cnt,hours = get_diurnal_dist(aws_30min[(aws_30min.stn_name==loc) & \
			(aws_30min.wind_gust>=5) & (aws_30min.wind_gust<15)])
		aws_30min_15_cnt,hours = get_diurnal_dist(aws_30min[(aws_30min.stn_name==loc) & \
			(aws_30min.wind_gust>=15) & (aws_30min.wind_gust<25)])
		aws_30min_25_cnt,hours = get_diurnal_dist(aws_30min[(aws_30min.stn_name==loc) & \
			(aws_30min.wind_gust>=25) & (aws_30min.wind_gust<30)])
		aws_30min_30_cnt,hours = get_diurnal_dist(aws_30min[(aws_30min.stn_name==loc) & \
			(aws_30min.wind_gust>=30)])

	#Get diurnal distribution for 6 hourly data
		plt.figure()
		plt.plot(hours,aws_30min_15_cnt,marker="s",linestyle="none",markersize=11)
		plt.plot(hours,aws_30min_25_cnt,marker="s",linestyle="none",markersize=11)
		plt.plot(hours,aws_30min_5_cnt,marker="s",linestyle="none",markersize=11)
		plt.plot(hours,aws_30min_30_cnt,marker="x",linestyle="none",color="k",\
				markeredgewidth=1.5,markersize=17.5)
		plt.ylabel("Count",fontsize="large")
		plt.xlabel("Hour (Local Time)",fontsize="large")
		plt.yscale("log")
		plt.title(loc)
		plt.xlim([0,24]);plt.ylim([0.5,plt.ylim()[1]])
		ax = plt.gca()
		ax.tick_params(labelsize=20)
		plt.grid()
		plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/temporal_distributions/"+\
			"diurnal_"+loc+".png",bbox_inches="tight")
		plt.close()


def plot_daily_data_monthly_dist(aws,stns,outname):

	#Plot seasonal distribution of wind gusts over certain thresholds for each AWS station
	s = 11
	no_years = float(2018-1979)
	for i in np.arange(0,len(stns)):
		fig = plt.figure(figsize=[8,6])
		aws_mth_cnt5,mths = get_monthly_dist(aws[(aws.stn_name==stns[i])],\
			threshold=[5,15])
		aws_mth_cnt15,mths = get_monthly_dist(aws[(aws.stn_name==stns[i])],\
			threshold=[15,25])
		aws_mth_cnt25,mths = get_monthly_dist(aws[(aws.stn_name==stns[i])],\
			threshold=[25,30])
		aws_mth_cnt30,mths = get_monthly_dist(aws[(aws.stn_name==stns[i])],\
			threshold=[30])
		plt.plot(mths,aws_mth_cnt15/no_years,linestyle="none",marker="s",markersize=s)
		plt.plot(mths,aws_mth_cnt25/no_years,linestyle="none",marker="s",markersize=s)
		plt.plot(mths,aws_mth_cnt5/no_years,linestyle="none",marker="s",markersize=s)
		plt.plot(mths,aws_mth_cnt30/no_years,linestyle="none",marker="x",markersize=17.5,color="k",\
			markeredgewidth=1.5)
		plt.title(stns[i],fontsize="xx-large")
		plt.xlabel("Month",fontsize="xx-large");plt.ylabel("Gusts per month",fontsize="xx-large")
		#plt.legend(loc="upper left")
		ax=plt.gca();ax.set_yscale('log')
		ax.set_xticks(np.arange(1,13,1))
		ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"])
		ax.set_xlim([0.01,12.5])
		ax.set_ylim([0.01,ax.get_ylim()[1]])
		ax.tick_params(labelsize="xx-large")
		ax.grid()
		fig.subplots_adjust(bottom=0.2)
		plt.savefig("/short/eg3/ab4502/figs/ExtremeWind/"\
			+outname+"_"+"monthly_"+stns[i]+"_1979_2017.tiff",bbox_inches="tight")
		#plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/temporal_distributions/"\
		#	+outname+"_"+"monthly_"+stns[i]+"_1979_2017.png")
		plt.close()

def get_diurnal_dist(aws):
	hours = np.arange(0,24,1)
	hour_counts = np.empty(len(hours))
	for h in np.arange(0,len(hours)):
		hour_counts[h] = (aws.hour==hours[h]).sum()
	return hour_counts,hours

def get_monthly_dist(aws,threshold=0,mean=False):
	#Get the distribution of months in a dataframe. If threshold is specified, restrict the 
	# dataframe to where the field "wind_gust" is above that threshold
	#If mean = "var", then also get the monthly mean for "var"
	months = np.sort(aws.month.unique())
	month_counts = np.empty(len(months))
	month_mean = np.empty(len(months))
	for m in np.arange(0,len(months)):
		if len(threshold)==1:
			month_count = ((aws[aws.wind_gust>=threshold[0]].month==months[m]).sum())
		elif len(threshold)==2:
			month_count = ((aws[(aws.wind_gust>=threshold[0]) & \
				(aws.wind_gust<threshold[1])].month==months[m]).sum())
		total_month = ((aws.month==months[m]).sum())
		#month_counts[m] = month_count / float(total_month)
		#month_counts[m] = month_count / float(aws[aws.wind_gust>=threshold].shape[0])
		month_counts[m] = month_count
		if mean != False:
			month_mean[m] = aws[aws.month==months[m]][mean].mean()
	if mean != False:
		return month_counts,month_mean,months
	else:
		return month_counts,months

def plot_stations():
	aws = pd.read_pickle("/short/eg3/ab4502/ExtremeWind/aws/"+\
		"all_daily_max_wind_gusts_sa_1979_2017.pkl")
	stns = aws.stn_name.unique()
	lons = aws.lon.unique()
	lats = aws.lat.unique()
	#remove Port Augusta power station coordinates, as it has merged with Port Augusta in aws df
	lats = lats[~(lats==-32.528)]
	lons = lons[~(lons==137.79)]
	
	start_lat = -38; end_lat = -26; start_lon = 132; end_lon = 142
	m = Basemap(llcrnrlon=start_lon, llcrnrlat=start_lat, urcrnrlon=end_lon, urcrnrlat=end_lat,\
		projection="cyl",resolution="i")
	m.drawcoastlines()

	for i in np.arange(0,len(stns)):
		x,y = m(lons[i],lats[i])
		plt.annotate(stns[i],xy=(x,y),color="k",size="small")
		plt.plot(x,y,"ro")
	plt.show()

if __name__ == "__main__":

	path = '/g/data/eg3/ab4502/ExtremeWind/aus/'
	f = "erai_wrf_20140622_20140624"
	model = "erai"
	fname = path+f+".nc"
	param = "cape*s06"
	region = "sa_small"

	time = [dt.datetime(2014,10,6,6,0,0),dt.datetime(2014,6,10,12,0,0)]
	outname = param+"_"+dt.datetime.strftime(time[0],"%Y%m%d_%H%M")+"_"+\
			dt.datetime.strftime(time[-1],"%Y%m%d_%H%M")

	#NOTE PUT IN FUNCTION
	if region == "aus":
	    start_lat = -44.525; end_lat = -9.975; start_lon = 111.975; end_lon = 156.275
	elif region == "sa_small":
	    start_lat = -38; end_lat = -26; start_lon = 132; end_lon = 142
	elif region == "sa_large":
	    start_lat = -40; end_lat = -24; start_lon = 112; end_lon = 156
	else:
	    raise NameError("Region must be one of ""aus"", ""sa_small"" or ""sa_large""")
	domain = [start_lat,end_lat,start_lon,end_lon]

#	PLOT SEASONAL DISTRIBUTIONS
	#plot_daily_data_monthly_dist(pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/"+\
	#	"erai_fc_points_1979_2017_daily_max.pkl").reset_index().\
	#	rename(columns={"wg10":"wind_gust","loc_id":"stn_name"}),\
	#	["Adelaide AP","Woomera","Mount Gambier","Port Augusta"],outname="ERA-Interim")
	barra_r_df = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_r_fc/"+\
		"barra_r_fc_points_daily_2003_2016.pkl").reset_index()
	barra_r_df["month"] = [t.month for t in barra_r_df.date]
	plot_daily_data_monthly_dist(barra_r_df.rename(columns={"max_wg10":"wind_gust","loc_id":"stn_name"}),\
		["Adelaide AP","Woomera","Mount Gambier","Port Augusta"],outname="BARRA-R")
	#plot_daily_data_monthly_dist(remove_incomplete_aws_years(\
	#		pd.read_pickle("/short/eg3/ab4502/ExtremeWind/aws/"+\
	#		"all_daily_max_wind_gusts_sa_1979_2017.pkl"),"Port Augusta").reset_index()\
	#		,["Adelaide AP","Woomera","Mount Gambier","Port Augusta"],outname="AWS")
	barra_ad_df = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_ad/"+\
		"barra_ad_points_daily_2006_2016.pkl").reset_index()
	barra_ad_df["month"] = [t.month for t in barra_ad_df.date]
	plot_daily_data_monthly_dist(barra_ad_df.rename(columns={"max_wg10":"wind_gust","loc_id":"stn_name"}),\
		["Adelaide AP","Woomera","Mount Gambier","Port Augusta"],outname="BARRA-AD")

	#CASE STUDIES
	#for time in date_seq([dt.datetime(1979,11,14,0),dt.datetime(1979,11,14,12)],"hours",6):
	#	plot_netcdf(domain,"/g/data/eg3/ab4502/ExtremeWind/sa_small/erai/"+\
	#		"erai_19791101_19791130.nc"\
	#		,"event_1979_"+time.strftime("%Y%m%d%H"),\
	#		[time],"erai",vars=["scp"])
	#for time in date_seq([dt.datetime(2016,9,28,0),dt.datetime(2016,9,28,12)],"hours",6):
	#	plot_netcdf(domain,"/g/data/eg3/ab4502/ExtremeWind/sa_small/erai/"+\
	#		"erai_20160901_20160930.nc"\
	#		,"system_black_"+time.strftime("%Y%m%d%H"),\
	#		[time],"erai",vars=["scp"])
	#for time in date_seq([dt.datetime(2016,9,28,0),dt.datetime(2016,9,28,12)],"hours",6):
	#	plot_netcdf(domain,"/g/data/eg3/ab4502/ExtremeWind/sa_small/barra/"+\
	#		"barra_20160901_20160930.nc"\
	#		,"system_black_"+time.strftime("%Y%m%d%H"),\
	#		[time],"barra",vars=["scp"])
	#for time in date_seq([dt.datetime(2016,9,28,0),dt.datetime(2016,9,28,12)],"hours",6):
	#	plot_netcdf(domain,"/g/data/eg3/ab4502/ExtremeWind/sa_small/barra_ad/"+\
	#		"barra_ad_20160928_20160929.nc"\
	#		,"system_black_"+time.strftime("%Y%m%d%H"),\
	#		[time],"barra_ad",vars=["scp"])

#	PLOT OBSERVED DIURNAL DISTRIBUTION
	#plot_diurnal_wind_distribution()
