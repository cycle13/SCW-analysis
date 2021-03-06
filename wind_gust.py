#Load point-based daily max wind gust data (reanalyisis and aws) and compare

import matplotlib.colors as colors
from scipy.stats import spearmanr as rho
from statsmodels.distributions.empirical_distribution import ECDF
from event_analysis import *
from plot_param import *
import matplotlib
#matplotlib.use("TkAgg")

def load_wind_gusts(include_barra,remove_incomplete_years='True'):
	#Load dataframes
	aws = pd.read_pickle("/short/eg3/ab4502/ExtremeWind/aws/all_daily_max_wind_gusts_sa_1979_2017.pkl")
	if remove_incomplete_years:
		aws = remove_incomplete_aws_years(aws,"Port Augusta")
	erai = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/"+\
		"erai_fc_points_1979_2017_daily_max.pkl")

	#Combine ERA-Interim, AWS and BARRA-R daily max wind gusts 
	if include_barra:
	    #barra_r = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_r_fc/"+\
	#		"barra_r_fc_points_daily_2003_2016.pkl")
	    barra_r = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/"+\
			"barra_r_fc_points_sa_small_2003_2016_daily_max_6hr.pkl")
	    barra_ad = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_ad/"+\
			"barra_ad_points_daily_2006_2016.pkl")
	    combined = pd.concat([aws.set_index(["date","stn_name"]).\
		rename(columns={"wind_gust":"aws_gust"})\
		,erai.set_index(["date","loc_id"]).rename(columns={"wg10":"erai_gust"}).erai_gust,\
		barra_ad.reset_index().set_index(["date","loc_id"]).\
		rename(columns={"max_max_wg10":"barra_ad_max_gust",\
		"max_wg10":"barra_ad_gust"})[["barra_ad_max_gust","barra_ad_gust"]],
		barra_r.reset_index().set_index(["date","loc_id"]).\
		rename(columns={"max_wg10":"barra_r_gust"}).barra_r_gust,\
		],axis=1).dropna()
	else:
	    combined = pd.concat([aws.set_index(["date","stn_name"]).\
		rename(columns={"wind_gust":"aws_gust"})\
		,erai.set_index(["date","loc_id"]).rename(columns={"wg10":"erai_gust"}).erai_gust,]\
		,axis=1).dropna()

	return combined

def resample_barra():
	#Take BARRA-R and BARRA-AD data at hourly frequency. Resample to daily max and save 
	#(HAS BEEN SAVED, NOW JUST LOAD)
	
	barra_r = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_r_fc/"+\
		"barra_r_fc_points_2006_2016.pkl")
	barra_r = eliminate_wind_gust_spikes(barra_r.set_index(["date","loc_id"]),"max_wg10")\
			.reset_index()
	barra_r_1d = pd.DataFrame()
	stns = np.unique(barra_r.loc_id)
	for stn in stns:
		print(stn)
		barra_r_1d = barra_r_1d.append(barra_r[barra_r.loc_id==stn].\
			set_index("date").resample("1D").max())
	barra_r_1d.to_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_r_fc/"\
		"barra_r_fc_points_daily_2006_2016.pkl")

	#barra_r = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_ad/"+\
	#	"barra_ad_points_mean_2006_2016.pkl")
	#barra_r = eliminate_wind_gust_spikes(barra_r.set_index(["date","loc_id"]),"max_wg10")\
	#		.reset_index()
	#barra_r_1d = pd.DataFrame()
	#stns = np.unique(barra_r.loc_id)
	#for stn in stns:
	#	print(stn)
	#	barra_r_1d = barra_r_1d.append(barra_r[barra_r.loc_id==stn].\
	#		set_index("date").resample("1D").max())
	#barra_r_1d.to_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_ad/"\
	#	"barra_ad_points_mean_daily_2006_2016.pkl")

#	barra_ad = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_ad/barra_ad_points_2006_2016.pkl")
#	barra_ad_1d = pd.DataFrame()
#	stns = np.unique(barra_ad.loc_id)
#	for stn in stns:
#		print(stn)
#		barra_ad_1d = barra_ad_1d.append(barra_ad[barra_ad.loc_id==stn].\
#			set_index("date").resample("1D").max())
#	barra_ad_1d.to_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_ad/"\
#		"barra_ad_points_daily_2006_2016.pkl")

def eliminate_wind_gust_spikes(df,mod_name):

	#Take an hourly gust dataframe. Consider all gusts above 40 m/s (likely to be a wind gust 
	# spike). If the previous and next hour are both below 20 m/s, disregard the gust. Replace
	# with the mean of the previous and next hour

	gust_df = df[df[mod_name]>=40]
	for i in np.arange(0,gust_df.shape[0]):
		prev_gust = df.loc[(gust_df.index[i][0]+dt.timedelta(hours=-1),gust_df.index[i][1])][mod_name]
		next_gust = df.loc[(gust_df.index[i][0]+dt.timedelta(hours=1),gust_df.index[i][1])][mod_name]
		if (prev_gust < 20) & (next_gust < 20):
			df.loc[((gust_df.index[i][0],gust_df.index[i][1]),mod_name)] = \
				(prev_gust + next_gust) / 2
	return df

def quantile_match(combined,obs_name,model_name):
	#Quantile matching
	#Note that currently, scenario is the same data as used to construct the observed 
	#	distribution (i.e. no cross-validation)
	#Note that model is matched to a combined distribution of all AWS stations

	#Create cumuliative distribution functions
	obs_cdf = ECDF(combined[obs_name])
	model_cdf = ECDF(combined[model_name])
	obs_invcdf = np.percentile(obs_cdf.x,obs_cdf.y*100)

	#Match model wind gust to the observed quantile distribution
	scenario_model = combined[model_name]
	scenario_obs = combined[obs_name]
	model_p = np.interp(scenario_model,model_cdf.x,model_cdf.y)
	model_xhat = np.interp(model_p,obs_cdf.y,obs_invcdf)

	#The 0th percentile wind gust is always matched to a NaN (due to interp function). Match
	# to the min observed instead
	model_xhat[np.isnan(model_xhat)] = obs_cdf.x[1]
	
	#Add quantile matched values to dataframe
	combined[(model_name + "_qm")] = model_xhat
	
	return combined

def plot_scatter(combined,model_list,name_list,location=False):
	fig = plt.figure(figsize=[15,7])
	if location != False:
		combined = combined[combined.index.get_level_values(1) == location]

	for n in np.arange(0,len(model_list)):
		plt.subplot(1,len(model_list),n+1)
		mod_rho = rho(combined["aws_gust"],combined[model_list[n]]).correlation
		bias = np.mean(combined[model_list[n]]) / np.mean(combined["aws_gust"])
		mae = np.mean(combined[model_list[n]] - combined["aws_gust"])
		rmse = np.sqrt(np.mean(np.power((combined[model_list[n]] - combined["aws_gust"]),2)))
		leg = "r = " + str(round(mod_rho,3)) + "\nMAE = " + str(round(mae,3)) + "\nRMSE = "+\
				str(round(rmse,3))
		#plt.scatter(combined["aws_gust"],combined[model_list[n]],label=leg)
		plt.scatter(combined[combined["aws_gust"]>=30]["aws_gust"],\
				combined[combined["aws_gust"]>=30][model_list[n]],color="k",marker="o")
		h = plt.hist2d(combined["aws_gust"],combined[model_list[n]],\
				bins=20,range=[[0,40],[0,40]],norm=colors.LogNorm(.1,1000),cmap=plt.get_cmap("Greys",8))
		#plt.legend(numpoints=0,fontsize="xx-large",loc=2)
		plt.plot([0,50],[0,50],"r")
		plt.xlim([0,40])
		plt.ylim([0,40])
		ax = plt.gca()
		ax.tick_params(labelsize="xx-large")
		ax.annotate(leg, xy=(2,39), xycoords='data',size="xx-large",ha="left",va="top",\
				bbox=dict(boxstyle='round', fc='w'))
		if n==1:
			ax.set_title(location,fontsize="xx-large")
		if location != "Mount Gambier":
			ax = plt.gca()
			ax.set_xticklabels("")			
		else:
			ax = plt.gca()
			ax.set_xticks([0,10,20,30,40])			
			ax.set_xticklabels(['0','10','20','30','40'])			
			if (n == 1) | (n == 2):
				ax.set_yticklabels("")	
			cax = fig.add_axes([0.2,0.05,0.6,0.01])
			cb = plt.colorbar(h[-1],cax,orientation="horizontal",extend="max")
			cb.ax.tick_params(labelsize="xx-large")
		if n>0:
			ax = plt.gca()
			ax.set_yticklabels("")			
	#plt.savefig("/short/eg3/ab4502/figs/ExtremeWind/scatter_"+location+".tiff",\
	#	bbox_inches="tight")
	#plt.savefig("/home/548/ab4502/working/ExtremeWind/figs/scatter/aws/"+location+".png",\
	#	bbox_inches="tight")
	plt.show()
	#plt.close()

def plot_monthly_dist(combined,gust_list,threshold):
	for n in np.arange(0,len(gust_list)):
		cnt, months = get_monthly_dist(combined.rename(columns={gust_list[n]:"wind_gust"})\
				,20)
		plt.plot(months,cnt,label = gust_list[n])
		plt.legend(loc=2)
	plt.show()

def plot_extreme_dist(combined,model_list,threshold,bins,log=False,normed=True):

	#For days with high AWS gusts (defined by threshold), what do re-analysis dists look like

	data = list()
	for n in np.arange(0,len(model_list)):
		df = combined[combined[model_list[n]]>=threshold]
		data.append(df[model_list[n]].values)

	plt.hist(data,histtype="bar",bins=bins,label=model_list,\
			normed=normed,range=[0,50],log=log)
	#plt.axvline(x=df.aws_gust.mean(),color="k",linestyle="--",label="Observed Mean")
	plt.legend()
	#plt.axvline(x=threshold,color="k")
	plt.xlim([threshold,50])
	plt.show()

def plot_extreme_dist_loc(combined,model_list,locations,threshold,bins,log=False):

	#For days with high AWS gusts (defined by threshold), what do re-analysis dists look like
	#Do for 4 locations
	
	combined = combined.reset_index().rename(columns={"level_0":"date","level_1":"loc_id"})
	for l in np.arange(0,len(locations)):
		plt.subplot(2,2,l+1)
		data = list()
		for n in np.arange(0,len(model_list)):
			df = combined[(combined[model_list[n]]>=threshold)&(combined.loc_id==locations[l])]
			data.append(df[model_list[n]].values)
		plt.hist(data,histtype="bar",bins=bins,label=model_list,\
			normed=False,range=[0,50],log=log)
		plt.title(locations[l])
	    #plt.axvline(x=df.aws_gust.mean(),color="k",linestyle="--",label="Observed Mean")
	    #plt.axvline(x=threshold,color="k")
		plt.xlim([threshold,45])
	plt.legend()
	plt.show()

def test_dist_assumption(combined,gust_type,stns=False,threshold=0):

	#If we are to use quantile matching between AWS data and each model, and apply to a gridded
	# dataset, then an underlying assumption is that the distribution of wind gust is the same
	# accross the entire state, and is the same as the distribution of the combined AWS data

	#We can test this by lookig at the mean/variance/max for each station
	#Producing a map of mean/variance for the sa_small domain in BARRA-R

	combined = combined.reset_index().rename(columns={"level_0":"date","level_1":"stn_name"})
	gust_type.append("aws_gust")
	cols = ["r","b"]
	if stns == False:
		stns = combined.stn_name.unique()
	plt.figure()
	aws = list()
	stn_lab = list()
	plot_cols = list()
	for s in np.arange(0,len(stns)):
		for n in np.arange(0,len(gust_type)):
			aws.append(combined[(combined.stn_name == stns[s]) & \
			(combined[gust_type[n]]>=threshold)][gust_type[n]].values)
			if n == 0:
				stn_lab.append(stns[s])
			else:
				stn_lab.append("")
			plot_cols.append(cols[n])
	
	for n in np.arange(0,len(gust_type)):
		if n == 0:
			stn_lab.append("Total")
		else:
			stn_lab.append("")
		aws.append(combined[combined[gust_type[n]]>=threshold][gust_type[n]].values)
		plot_cols.append(cols[n])
		plt.plot([0,1],[0,1],color=cols[n],label=gust_type[n])
	plt.legend()
	bp = plt.boxplot(aws,whis=1.5,labels=stn_lab)
	cnt = 0
	for patch in bp["boxes"]:
		patch.set(color=plot_cols[cnt])
		cnt=cnt+1
	plt.xticks(rotation="vertical")
	plt.subplots_adjust(bottom=0.30)
	#plt.title()
	plt.ylim([threshold-1,50])
	plt.axhline(30,color="grey")

	plt.show()

def reanalysis_check():

	import pandas as pd
	import numpy as np
	import matplotlib.pyplot as plt

	#Load in reanalysis gusts, and observations. Plot scatterplots, with convective and non-convective
	# gusts shown separately. Show lines of best fit
	barra = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barra_allvars_2005_2018_2.pkl")
	barpa = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/barpa_erai_gusts.pkl")
	era5 = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/points/era5_allvars_2005_2018.pkl")
	obs = pd.read_pickle("/g/data/eg3/ab4502/ExtremeWind/obs/aws/convective_wind_gust_aus_2005_2018.pkl")
	obs["hourly_ceil_utc"] = pd.DatetimeIndex(obs["gust_time_utc"]).ceil("1H")

	removed = ['Broome', 'Port Hedland', 'Carnarvon', 'Meekatharra', 'Perth', 'Esperance', 'Kalgoorlie', 'Halls Creek']
	barra = barra.loc[np.in1d(barra.loc_id, removed, invert=True)]
	era5 = era5.loc[np.in1d(era5.loc_id, removed, invert=True)]

	barra_sta_wg = pd.merge(obs[["stn_name","wind_gust","hourly_ceil_utc","tc_affected","lightning","is_sta"]],\
                barra, how="left",left_on=["stn_name","hourly_ceil_utc"], right_on=["loc_id","time"]).\
		dropna(subset=["ml_cape"])
	barra_aws_wg = barra_sta_wg.dropna(subset=["wind_gust"])
	era5_sta_wg = pd.merge(obs[["stn_name","wind_gust","hourly_ceil_utc","tc_affected","lightning","is_sta"]],\
                era5, how="left",left_on=["stn_name","hourly_ceil_utc"], right_on=["loc_id","time"]).\
		dropna(subset=["ml_cape"])
	era5_aws_wg = era5_sta_wg.dropna(subset=["wind_gust"])
	barpa_sta_wg = pd.merge(obs[["stn_name","wind_gust","daily_date_utc","tc_affected","lightning","is_sta"]],\
		barpa, how="left",left_on=["stn_name","daily_date_utc"], right_on=["loc_id","time"]).\
		dropna(subset=["max_wndgust10m"])      
	barpa_aws_wg = barpa_sta_wg.dropna(subset=["wind_gust"])

	#Find poly fits and correlations
	barra_conv_fit =np.polynomial.polynomial.Polynomial.fit(\
		    barra_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")\
		    ["wind_gust"], barra_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")["wg10"], 1)
	barra_conv_corr =np.corrcoef(\
		    barra_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")\
		    ["wind_gust"], barra_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")["wg10"])[1,0]
	barra_conv_fit_x, barra_conv_fit_y = barra_conv_fit.linspace(10)
	barra_non_conv_fit =np.polynomial.polynomial.Polynomial.fit(\
		    barra_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")\
		    ["wind_gust"], barra_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")["wg10"], 1)
	barra_non_conv_corr =np.corrcoef(\
		    barra_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")\
		    ["wind_gust"], barra_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")["wg10"])[1,0]
	barra_non_conv_fit_x, barra_non_conv_fit_y = barra_non_conv_fit.linspace(10)
	barra_tc_fit =np.polynomial.polynomial.Polynomial.fit(\
		    barra_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")\
		    ["wind_gust"], barra_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")["wg10"], 1)
	barra_tc_fit_x, barra_tc_fit_y = barra_tc_fit.linspace(10)
	barra_tc_corr =np.corrcoef(\
		    barra_aws_wg.query("(wind_gust >= 25) & (tc_affected == 1)")\
		    ["wind_gust"], barra_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")["wg10"])[1,0]

	barpa_conv_fit =np.polynomial.polynomial.Polynomial.fit(\
		    barpa_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")\
		    ["wind_gust"], barpa_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")["max_wndgust10m"], 1)
	barpa_conv_corr =np.corrcoef(\
		    barpa_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")\
		    ["wind_gust"], barpa_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")["max_wndgust10m"])[1,0]
	barpa_conv_fit_x, barpa_conv_fit_y = barpa_conv_fit.linspace(10)
	barpa_non_conv_fit =np.polynomial.polynomial.Polynomial.fit(\
		    barpa_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")\
		    ["wind_gust"], barpa_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")["max_wndgust10m"], 1)
	barpa_non_conv_corr =np.corrcoef(\
		    barpa_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")\
		    ["wind_gust"], barpa_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")["max_wndgust10m"])[1,0]
	barpa_non_conv_fit_x, barpa_non_conv_fit_y = barpa_non_conv_fit.linspace(10)
	barpa_tc_fit =np.polynomial.polynomial.Polynomial.fit(\
		    barpa_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")\
		    ["wind_gust"], barpa_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")["max_wndgust10m"], 1)
	barpa_tc_fit_x, barpa_tc_fit_y = barpa_tc_fit.linspace(10)
	barpa_tc_corr =np.corrcoef(\
		    barpa_aws_wg.query("(wind_gust >= 25) & (tc_affected == 1)")\
		    ["wind_gust"], barpa_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")["max_wndgust10m"])[1,0]

	era5_conv_fit =np.polynomial.polynomial.Polynomial.fit(\
		    era5_aws_wg.query("(wind_gust >= 25) & (lightning >= 2 & (tc_affected==0))")\
		    ["wind_gust"], era5_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")["wg10"], 1)
	era5_conv_corr =np.corrcoef(\
		    era5_aws_wg.query("(wind_gust >= 25) & (lightning >= 2 & (tc_affected==0))")\
		    ["wind_gust"], era5_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)")["wg10"])[1,0]
	era5_conv_fit_x, era5_conv_fit_y = era5_conv_fit.linspace(10)
	era5_non_conv_fit =np.polynomial.polynomial.Polynomial.fit(\
		    era5_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")\
		    ["wind_gust"], era5_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")["wg10"], 1)
	era5_non_conv_corr =np.corrcoef(\
		    era5_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")\
		    ["wind_gust"], era5_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)")["wg10"])[1,0]
	era5_non_conv_fit_x, era5_non_conv_fit_y = era5_non_conv_fit.linspace(10)
	era5_tc_fit =np.polynomial.polynomial.Polynomial.fit(\
		    era5_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")\
		    ["wind_gust"], era5_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)")["wg10"], 1)
	era5_tc_fit_x, era5_tc_fit_y = era5_tc_fit.linspace(10)
	era5_tc_corr =np.corrcoef(\
		    era5_aws_wg.query("(wind_gust >= 25) & (tc_affected == 1)")\
		    ["wind_gust"], era5_aws_wg.query("(wind_gust >= 25) & (tc_affected == 1)")["wg10"])[1,0]

	#Plot scatterplots for > 25 m/s
	plt.figure(figsize=[10,6]);plt.subplot(311);ax=plt.gca() 
	barra_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)").plot(kind="scatter",x="wind_gust",\
		y="wg10",marker="x",ax=ax, color="tab:blue",label="Non-conv: r="+str(round(barra_non_conv_corr,2)))
	barra_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)").plot(kind="scatter",x="wind_gust",\
		y="wg10",ax=ax,marker="o",color="none",edgecolor="r",label="Conv: r="+str(round(barra_conv_corr,2)))
	barra_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)").plot(kind="scatter",x="wind_gust",\
		y="wg10",ax=ax,marker="^",color="none",edgecolor="tab:green",\
		label="TC affected: r="+str(round(barra_tc_corr,2)))
	plt.plot([25,40],[25,40],color="k") 
	plt.plot(barra_conv_fit_x, barra_conv_fit_y, color="r")
	plt.plot(barra_non_conv_fit_x, barra_non_conv_fit_y, color="tab:blue")
	plt.plot(barra_tc_fit_x, barra_tc_fit_y, color="tab:green")
	plt.legend()
	plt.xlabel("")
	plt.ylabel("BARRA")
	plt.subplot(312);ax=plt.gca() 
	era5_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)").plot(kind="scatter",x="wind_gust",\
		y="wg10",marker="x",ax=ax, color="tab:blue",label="Non-conv: r="+str(round(era5_non_conv_corr,2)))
	era5_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)").plot(kind="scatter",x="wind_gust", \
		y="wg10",ax=ax,marker="o",color="none",edgecolor="r",label="Conv: r="+str(round(era5_conv_corr,2)))
	era5_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)").plot(kind="scatter",x="wind_gust",\
		y="wg10",ax=ax,marker="^",color="none",edgecolor="tab:green",\
		label="TC affected: r="+str(round(era5_tc_corr,2)))
	plt.plot([25,40],[25,40],color="k") 
	plt.plot(era5_conv_fit_x, era5_conv_fit_y, color="r")
	plt.plot(era5_non_conv_fit_x, era5_non_conv_fit_y, color="tab:blue")
	plt.plot(era5_tc_fit_x, era5_tc_fit_y, color="tab:green")
	plt.ylabel("ERA5")
	plt.subplot(313);ax=plt.gca() 
	barpa_aws_wg.query("(wind_gust >= 25) & (lightning < 2) & (tc_affected==0)").plot(kind="scatter",x="wind_gust",\
		y="max_wndgust10m",marker="x",ax=ax, color="tab:blue",label="Non-conv: r="+str(round(barpa_non_conv_corr,2)))
	barpa_aws_wg.query("(wind_gust >= 25) & (lightning >= 2) & (tc_affected==0)").plot(kind="scatter",x="wind_gust",\
		y="max_wndgust10m",ax=ax,marker="o",color="none",edgecolor="r",label="Conv: r="+str(round(barpa_conv_corr,2)))
	barpa_aws_wg.query("(wind_gust >= 25) & (tc_affected==1)").plot(kind="scatter",x="wind_gust",\
		y="max_wndgust10m",ax=ax,marker="^",color="none",edgecolor="tab:green",\
		label="TC affected: r="+str(round(barpa_tc_corr,2)))
	plt.plot([25,40],[25,40],color="k") 
	plt.plot(barpa_conv_fit_x, barpa_conv_fit_y, color="r")
	plt.plot(barpa_non_conv_fit_x, barpa_non_conv_fit_y, color="tab:blue")
	plt.plot(barpa_tc_fit_x, barpa_tc_fit_y, color="tab:green")
	plt.legend()
	plt.xlabel("")
	plt.ylabel("BARPA")
	plt.xlabel("AWS")

	#Plot scatterplots for all gusts
	plt.figure(figsize=[8,10])
	barra_fit = np.polynomial.polynomial.Polynomial.fit(barra_aws_wg["wind_gust"],barra_aws_wg["wg10"], 2)
	era5_fit = np.polynomial.polynomial.Polynomial.fit(era5_aws_wg["wind_gust"],era5_aws_wg["wg10"], 2)
	barpa_fit = np.polynomial.polynomial.Polynomial.fit(barpa_aws_wg["wind_gust"],barpa_aws_wg["max_wndgust10m"], 2)
	barra_fit_x, barra_fit_y = barra_fit.linspace(10)
	era5_fit_x, era5_fit_y = era5_fit.linspace(10)
	barpa_fit_x, barpa_fit_y = barpa_fit.linspace(10)
	plt.subplot(311);ax=plt.gca()
	barra_aws_wg.plot(kind="hexbin",x="wind_gust",y="wg10",ax=ax,gridsize=20, norm=colors.SymLogNorm(1), vmin=0, vmax=1000, cmap=plt.get_cmap("Oranges"), extent=(0, 40, 0, 40))
	#barra_aws_wg.plot(kind="hexbin",x="wind_gust",y="wg10",color="none",edgecolor="tab:blue",ax=ax)
	plt.plot(barra_fit_x,barra_fit_y,color="r")
	plt.plot([0,40],[0,40],"k"); plt.ylim([0,40]); plt.xlim([0,40])
	plt.ylabel("BARRA (m/s)");plt.xlabel("")
	r = np.corrcoef(barra_aws_wg["wind_gust"], barra_aws_wg["wg10"])
	plt.text(35, 5, "r = "+str(round(r[1,0],3)),va="center", ha="center")
	plt.subplot(312);ax=plt.gca()
	era5_aws_wg.plot(kind="hexbin",x="wind_gust",y="wg10",ax=ax,gridsize=20, norm=colors.SymLogNorm(1), vmin=0, vmax=1000, cmap=plt.get_cmap("Oranges"), extent=(0, 40, 0, 40))
	#era5_aws_wg.plot(kind="hexbin",x="wind_gust",y="wg10",color="none",edgecolor="tab:blue",ax=ax)
	plt.plot(era5_fit_x,era5_fit_y,color="r")
	plt.plot([0,40],[0,40],"k"); plt.ylim([0,40]); plt.xlim([0,40])
	plt.ylabel("ERA5 (m/s)");plt.xlabel("")
	r = np.corrcoef(era5_aws_wg["wind_gust"], era5_aws_wg["wg10"])
	plt.text(35, 5, "r = "+str(round(r[1,0],3)),va="center", ha="center")
	plt.subplot(313);ax=plt.gca()
	barpa_aws_wg.plot(kind="hexbin",x="wind_gust",y="max_wndgust10m",ax=ax,gridsize=20, norm=colors.SymLogNorm(1), vmin=0, vmax=1000, cmap=plt.get_cmap("Oranges"), extent=(0, 40, 0, 40))
	#barpa_aws_wg.plot(kind="scatter",x="wind_gust",y="max_wndgust10m",color="none",edgecolor="tab:blue",ax=ax)
	plt.plot(barra_fit_x,barpa_fit_y,color="r")
	plt.plot([0,40],[0,40],"k"); plt.ylim([0,40]); plt.xlim([0,40])
	plt.ylabel("BARPA (m/s)");plt.xlabel("AWS (m/s)")
	r = np.corrcoef(barpa_aws_wg["wind_gust"], barpa_aws_wg["max_wndgust10m"])
	plt.text(35, 5, "r = "+str(round(r[1,0],3)),va="center", ha="center")
	plt.savefig("/g/data/eg3/ab4502/figs/barpa/aws_gusts.png", bbox_inches="tight")

if __name__ == "__main__":
	#df = load_wind_gusts(True,remove_incomplete_years=False)
	#test_dist_assumption(df,["barra_r_gust"],stns=False,threshold=20)
	#[plot_scatter(df,["erai_gust","barra_r_gust","barra_ad_gust"],["ERA-Interim","BARRA-R","BARRA-AD"],\
	#	location=l) for l in ["Adelaide AP","Woomera","Port Augusta","Mount Gambier"]]
	reanalysis_check()
