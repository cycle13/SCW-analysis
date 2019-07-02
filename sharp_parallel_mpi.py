#Parallel sharppy using mpi

import pandas as pd
from erai_read import read_erai
from erai_read import get_mask as get_erai_mask
from barra_read import read_barra
from barra_read import get_mask as get_barra_mask
from calc_param import save_netcdf, get_dp
import datetime as dt
from mpi4py import MPI
import numpy as np
import sharppy.sharptab.profile as profile
import sharppy.sharptab.utils as utils
import sharppy.sharptab.params as params
import sharppy.sharptab.interp as interp
import sharppy.sharptab.winds as winds
import warnings
import sys

#---------------------------------------------------------------------------------------------------
#TO RUN:
# > mpiexec python sharp_parallel_mpi.py model region t1 t2 (out_name)
#
#	- model 
#		Is either "barra" or "erai"
#	- region
#		Is either "aus" or "sa_small"
#	- t1
#		Is the start time, specified by "YYYYMMDDHH"
#	- t2
#		Is the end time, specified by "YYYYMMDDHH"
#
#	- out_name
#		Optional, specifies the prefix of the netcdf output. If ommited,
#		out_name will be the same as model
#
#Before running
# > source activate sharppy
# > module load mpi4py/3.0.0-py3
# > module unload python3/3.6.2
#
#
#See line 160 for a list of parameters to get
#---------------------------------------------------------------------------------------------------

def sharp_parcel_mpi(p,ua,va,hgt,ta,dp,ps):

	#Exact same as sharp parcel, but intended to use the "mpi4py" module
	
	#Only use the part of the profile which is above the surface (i.e. where the pressure levels are less than
	# the surface pressure
	agl_idx = (p <= ps)

	#create profile
	prof = profile.create_profile(pres=p[agl_idx], hght=hgt[agl_idx], \
			tmpc=ta[agl_idx], \
			dwpc=dp[agl_idx], \
			u=ua[agl_idx], v=va[agl_idx],\
			strictqc=False)

	#create parcels
	sb_parcel = params.parcelx(prof, flag=1, dp=-10)
	mu_parcel = params.parcelx(prof, flag=3, dp=-10)
	ml_parcel = params.parcelx(prof, flag=4, dp=-10)
	eff_parcel = params.parcelx(prof, flag=6, ecape=100, ecinh=-250, dp=-10)
	return (prof, mu_parcel ,ml_parcel, sb_parcel, eff_parcel)

if __name__ == "__main__":

	#Ignore warnings from SHARPpy
	warnings.simplefilter("ignore")

	#Get MPI communicator info
	comm = MPI.COMM_WORLD
	size = comm.Get_size()
	rank = comm.Get_rank()
	
	#Load data into first processer (can be thought of as "local")
	if rank == 0:

		#Parse arguments from cmd line and set up inputs (date region model)
		model = sys.argv[1]
		region = sys.argv[2]
		t1 = sys.argv[3]
		t2 = sys.argv[4]
		if len(sys.argv) > 5:
			out_name = sys.argv[5]
		else:
			out_name = model

		if region == "sa_small":
			start_lat = -38; end_lat = -26; start_lon = 132; end_lon = 142
		elif region == "aus":
       	    		start_lat = -44.525; end_lat = -9.975; start_lon = 111.975; end_lon = 156.275
		else:
			raise ValueError("INVALID REGION\n")

		domain = [start_lat,end_lat,start_lon,end_lon]

		try:
			time = [dt.datetime.strptime(t1,"%Y%m%d%H"),dt.datetime.strptime(t2,"%Y%m%d%H")]
		except:
			raise ValueError("INVALID START OR END TIME. SHOULD BE YYYYMMDDHH\n")

		#Load data and setup base array, which has been reformed into a 2d array, with rows as 
		# spatial-temporal coordinates and columns as vertical levels
		if model == "erai":
			ta,temp1,hur,hgt,terrain,p,ps,ua,va,uas,vas,cp,wg10,cape,lon,lat,date_list = \
				read_erai(domain,time)
			dp = get_dp(hur=hur, ta=ta)
			lsm = np.repeat(get_erai_mask(lon,lat)[np.newaxis],ta.shape[0],0)
		elif model == "barra":
			ta,temp1,hur,hgt,terrain,p,ps,ua,va,uas,vas,wg10,lon,lat,date_list = \
				read_barra(domain,time)
			dp = get_dp(hur=hur, ta=ta)
			lsm = np.repeat(get_barra_mask(lon,lat)[np.newaxis],ta.shape[0],0)
		else:
			raise ValueError("INVALID MODEL NAME\n")
		
		orig_shape = ta.shape
		ta = np.moveaxis(ta,[0,1,2,3],[0,3,1,2]).\
			reshape((ta.shape[0]*ta.shape[2]*ta.shape[3],ta.shape[1])).astype("double",order="C")
		dp = np.moveaxis(dp,[0,1,2,3],[0,3,1,2]).\
			reshape((dp.shape[0]*dp.shape[2]*dp.shape[3],dp.shape[1])).astype("double",order="C")
		hur = np.moveaxis(hur,[0,1,2,3],[0,3,1,2]).\
			reshape((hur.shape[0]*hur.shape[2]*hur.shape[3],hur.shape[1])).astype("double",order="C")
		hgt = np.moveaxis(hgt,[0,1,2,3],[0,3,1,2]).\
			reshape((hgt.shape[0]*hgt.shape[2]*hgt.shape[3],hgt.shape[1])).astype("double",order="C")
		ua = utils.MS2KTS(np.moveaxis(ua,[0,1,2,3],[0,3,1,2]).\
			reshape((ua.shape[0]*ua.shape[2]*ua.shape[3],ua.shape[1]))).astype("double",order="C")
		va = utils.MS2KTS(np.moveaxis(va,[0,1,2,3],[0,3,1,2]).\
			reshape((va.shape[0]*va.shape[2]*va.shape[3],va.shape[1]))).astype("double",order="C")
		uas = utils.MS2KTS(uas.reshape((uas.shape[0]*uas.shape[1]*uas.shape[2]))).astype("double",order="C")
		vas = utils.MS2KTS(vas.reshape((vas.shape[0]*vas.shape[1]*vas.shape[2]))).astype("double",order="C")
		ps = ps.reshape((ps.shape[0]*ps.shape[1]*ps.shape[2])).astype("double",order="C")
		wg10 = wg10.reshape((wg10.shape[0]*wg10.shape[1]*wg10.shape[2])).astype("double",order="C")
		lsm = np.array(lsm.reshape((lsm.shape[0]*lsm.shape[1]*lsm.shape[2]))).astype("double",order="C")
		if model == "erai":
			cape = cape.reshape((cape.shape[0]*cape.shape[1]*cape.shape[2])).astype("double",order="C")
			cp = cp.reshape((cp.shape[0]*cp.shape[1]*cp.shape[2])).astype("double",order="C")
		
		#Restricting base data to land points
		orig_length = ta.shape[0]
		lsm_orig = lsm
		ta = ta[lsm==1]
		dp = dp[lsm==1]
		hur = hur[lsm==1]
		hgt = hgt[lsm==1]
		ua = ua[lsm==1]
		va = va[lsm==1]
		uas = uas[lsm==1]
		vas = vas[lsm==1]
		ps = ps[lsm==1]
		wg10 = wg10[lsm==1]
		if model == "erai":
			cp = cp[lsm==1]
			cape = cape[lsm==1]
		lsm = lsm[lsm==1]

		#Set the ouput array (in this case, a vector with length given by the number of spatial-temporal 
		# points)
		param = np.array(["ml_cape", "mu_cape", "sb_cape", "ml_cin", "sb_cin", "mu_cin",\
					"ml_lcl", "mu_lcl", "sb_lcl", "eff_cape", "eff_cin", "eff_lcl", "dcape", \
					"lr01", "lr03", "lr13", "lr36", "lr_freezing",\
					"qmean01", "qmean03", "qmean06", "qmean13", "qmean36", "qmeansubcloud", \
					"q_melting", "q1", "q3", "q6",\
					"rhmin01", "rhmin03", "rhmin06", "rhmin13", "rhmin36", "rhminsubcloud", \
					"mhgt", "el", "pwat", "v_totals", "c_totals", "t_totals",
					\
					"cp", "cape", "dcp2", "cape*s06",\
					\
					"srhe", "srh01", "srh03", "srh06", \
					"ebwd", "s06", "s03", "s01", "s13", "s36", "scld", \
					"U500", "U10", "U1", "U3", "U6", \
					"Ust", "Usr01", "Usr03", "Usr06", "Usr13", "Usr36", \
					"Uwindinf", "Umeanwindinf", "Umean800_600", "Umean06", \
					"wg10",\
					\
					"dcp", "stp_cin", "stp_fixed", "scp", "ship",\
					"mlcape*s06", "mucape*s06", "dmgwind", \
					"ducs6", "convgust","windex","gustex", "gustex2","gustex3",\
					"eff_sherb", "sherb", "wndg","mburst","sweat"])
		output_data = np.zeros((ta.shape[0], len(param)))
		effective_layer_params = ["srhe", "ebwd", "Uwindinf", "stp_cin", "dcp", "Umeanwindinf", "scp", \
						"dmgwind", "scld", "eff_sherb"]
		if len(param) != len(np.unique(param)):
			unique_params, name_cts = np.unique(param,return_counts=True)
			raise ValueError("THE FOLLOWING PARAMS HAVE BEEN ENTERED TWICE IN THE PARAM LIST %s" %(unique_params[name_cts>1],))

		#Split/chunk the base arrays on the spatial-temporal grid point dimension, for parallel processing
		ta_split = np.array_split(ta, size, axis = 0)
		dp_split = np.array_split(dp, size, axis = 0)
		hur_split = np.array_split(hgt, size, axis = 0)
		hgt_split = np.array_split(hgt, size, axis = 0)
		ua_split = np.array_split(ua, size, axis = 0)
		va_split = np.array_split(va, size, axis = 0)
		uas_split = np.array_split(uas, size, axis = 0)
		vas_split = np.array_split(vas, size, axis = 0)
		ps_split = np.array_split(ps, size, axis = 0)
		wg10_split = np.array_split(wg10, size, axis = 0)
		if model == "erai":
			cape_split = np.array_split(cape, size, axis = 0)
			cp_split = np.array_split(cp, size, axis = 0)
		lsm_split = np.array_split(lsm, size, axis = 0)
		split_sizes = []
		for i in range(0,len(ta_split),1):
			split_sizes = np.append(split_sizes, ta_split[i].shape[0])

		#Remember the points at which splits occur on (noting that Gatherv and Scatterv act on a 
		# "C" style (row-major) flattened array)
		split_sizes_input = split_sizes*ta.shape[1]
		displacements_input = np.insert(np.cumsum(split_sizes_input),0,0)[0:-1]
		split_sizes_output = split_sizes*len(param)
		displacements_output = np.insert(np.cumsum(split_sizes_output),0,0)[0:-1]
		split_sizes_input_2d = split_sizes
		displacements_input_2d = np.insert(np.cumsum(split_sizes_input_2d),0,0)[0:-1]

	else:
		#Initialise variables on other cores, including the name of the model
		model = sys.argv[1]
		split_sizes_input = None; displacements_input = None; split_sizes_output = None;\
			displacements_output = None; split_sizes_input_2d = None; displacements_input_2d = None
		ta_split = None; dp_split = None; hur_split = None; hgt_split = None; ua_split = None;\
			va_split = None; uas_split = None; vas_split = None; lsm_split = None;\
			wg10_split = None; ps_split = None
		ta = None; dp = None; hur = None; hgt = None; ua = None;\
			va = None; uas = None; vas = None; lsm = None; wg10 = None; ps = None
		p = None
		output_data = None
		param = None
		if model == "erai":
			cape_split = None; cp_split = None; cape = None; cp = None

	#Broadcast split arrays to other cores
	ta_split = comm.bcast(ta_split, root=0)
	dp_split = comm.bcast(dp_split, root=0)
	hur_split = comm.bcast(hur_split, root=0)
	hgt_split = comm.bcast(hgt_split, root=0)
	ua_split = comm.bcast(ua_split, root=0)
	va_split = comm.bcast(va_split, root=0)
	uas_split = comm.bcast(uas_split, root=0)
	vas_split = comm.bcast(vas_split, root=0)
	ps_split = comm.bcast(ps_split, root=0)
	wg10_split = comm.bcast(wg10_split, root=0)
	if model == "erai":
		cp_split = comm.bcast(cp_split, root=0)
		cape_split = comm.bcast(cape_split, root=0)
	lsm_split = comm.bcast(lsm_split, root=0)
	p = comm.bcast(p, root=0)
	param = comm.bcast(param, root=0)
	split_sizes_input = comm.bcast(split_sizes_input, root = 0)
	displacements_input = comm.bcast(displacements_input, root = 0)
	split_sizes_output = comm.bcast(split_sizes_output, root = 0)
	displacements_output = comm.bcast(displacements_output, root = 0)

	#Create arrays to receive chunked/split data on each core, where rank specifies the core
	ta_chunk = np.zeros(np.shape(ta_split[rank]))
	dp_chunk = np.zeros(np.shape(dp_split[rank]))
	hur_chunk = np.zeros(np.shape(hur_split[rank]))
	hgt_chunk = np.zeros(np.shape(hgt_split[rank]))
	ua_chunk = np.zeros(np.shape(ua_split[rank]))
	va_chunk = np.zeros(np.shape(va_split[rank]))
	uas_chunk = np.zeros(np.shape(uas_split[rank]))
	vas_chunk = np.zeros(np.shape(vas_split[rank]))
	ps_chunk = np.zeros(np.shape(ps_split[rank]))
	wg10_chunk = np.zeros(np.shape(wg10_split[rank]))
	lsm_chunk = np.zeros(np.shape(lsm_split[rank]))
	comm.Scatterv([ta,split_sizes_input, displacements_input, MPI.DOUBLE],ta_chunk,root=0)
	comm.Scatterv([dp,split_sizes_input, displacements_input, MPI.DOUBLE],dp_chunk,root=0)
	comm.Scatterv([hur,split_sizes_input, displacements_input, MPI.DOUBLE],hur_chunk,root=0)
	comm.Scatterv([hgt,split_sizes_input, displacements_input, MPI.DOUBLE],hgt_chunk,root=0)
	comm.Scatterv([ua,split_sizes_input, displacements_input, MPI.DOUBLE],ua_chunk,root=0)
	comm.Scatterv([va,split_sizes_input, displacements_input, MPI.DOUBLE],va_chunk,root=0)
	comm.Scatterv([uas,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],uas_chunk,root=0)
	comm.Scatterv([vas,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],vas_chunk,root=0)
	comm.Scatterv([ps,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],ps_chunk,root=0)
	comm.Scatterv([wg10,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],wg10_chunk,root=0)
	comm.Scatterv([lsm,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],lsm_chunk,root=0)
	if model == "erai":
		cp_chunk = np.zeros(np.shape(cp_split[rank]))
		cape_chunk = np.zeros(np.shape(cape_split[rank]))
		comm.Scatterv([cp,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],cp_chunk,root=0)
		comm.Scatterv([cape,split_sizes_input_2d, displacements_input_2d, MPI.DOUBLE],cape_chunk,root=0)

	comm.Barrier()

#----------------------------------------------------------------------------------------------------------------
	#Run SHARPpy
	start = dt.datetime.now()
	output = np.zeros((ta_chunk.shape[0],len(param)))
	for i in np.arange(0,ta_chunk.shape[0]):
		#Get profile and parcels
		prof, mu_pcl ,ml_pcl, sb_pcl, eff_pcl= sharp_parcel_mpi(p, \
			ua_chunk[i],\
			va_chunk[i],\
			hgt_chunk[i],\
			ta_chunk[i],\
			dp_chunk[i],\
			ps_chunk[i])

		#Extract varibales relevant for output
		#Levels
		sfc = prof.pres[prof.sfc]
		p1km = interp.pres(prof, interp.to_msl(prof, 1000.))
		p3km = interp.pres(prof, interp.to_msl(prof, 3000.))
		p6km = interp.pres(prof, interp.to_msl(prof, 6000.))
		melting_hgt = ml_pcl.hght0c
		pmelting_hgt = interp.pres(prof, interp.to_msl(prof, melting_hgt))
		pcld = interp.pres(prof, interp.to_msl(prof, 0.5 * mu_pcl.elhght))
		pmllcl = interp.pres(prof, interp.to_msl(prof, ml_pcl.lclhght))
		#Effective (inflow) layer
		ebotp, etopp = params.effective_inflow_layer(prof, mupcl=mu_pcl, ecape=100, ecinh=-250)
		ebot_hgt = interp.to_agl(prof, interp.hght(prof,ebotp))
		etop_hgt = interp.to_agl(prof, interp.hght(prof,etopp))
		#Winds
		u01, v01 = interp.components(prof, p1km)
		u03, v03 = interp.components(prof, p3km)
		u06, v06 = interp.components(prof, p6km)
		u500, v500 = interp.components(prof, 500)
		umllcl, vmllcl = interp.components(prof, pmllcl)
		ucld, vcld = interp.components(prof, pcld)
		s01 = np.array(np.sqrt(np.square(u01-uas_chunk[i])+np.square(v01-vas_chunk[i])))
		s03 = np.array(np.sqrt(np.square(u03-uas_chunk[i])+np.square(v03-vas_chunk[i])))
		s06 = np.array(np.sqrt(np.square(u06-uas_chunk[i])+np.square(v06-vas_chunk[i])))
		s13 = np.array(np.sqrt(np.square(u03-u01)+np.square(v03-v01)))
		s36 = np.array(np.sqrt(np.square(u06-u03)+np.square(v06-v03)))
		scld = np.array(np.sqrt(np.square(ucld-umllcl)+np.square(vcld-vmllcl)))
		umean01 , vmean01 = winds.mean_wind(prof, pbot = sfc, ptop = p6km)
		umean03 , vmean03 = winds.mean_wind(prof, pbot = sfc, ptop = p6km)
		umean06 , vmean06 = winds.mean_wind(prof, pbot = sfc, ptop = p6km)
		umean800_600 , vmean800_600 = winds.mean_wind(prof, pbot = 800, ptop = 600)
		Umean01 = utils.mag(umean01, vmean01)
		Umean03 = utils.mag(umean03, vmean03)
		Umean06 = utils.mag(umean06, vmean06)
		Umean800_600 = utils.mag(umean800_600, vmean800_600)
		U500 = utils.mag(u500, v500)
		U1 = utils.mag(u01, v01)
		U3 = utils.mag(u03, v03)
		U6 = utils.mag(u06, v06)

		#Storm relative winds/effective inflow layer winds
		stu, stv, temp1, temp2 = winds.non_parcel_bunkers_motion(prof)
		Ust = utils.mag(stu,stv)
		uwindinf, vwindinf = interp.components(prof, etopp)
		Uwindinf = utils.mag(uwindinf, vwindinf)
		umeanwindinf , vmeanwindinf = winds.mean_wind(prof, pbot = ebotp, ptop = etopp)
		Umeanwindinf = utils.mag(umeanwindinf, vmeanwindinf)
		usr01, vsr01 = winds.sr_wind(prof, pbot=sfc, ptop=p1km, stu=stu, stv=stv)
		usr03, vsr03 = winds.sr_wind(prof, pbot=sfc, ptop=p3km, stu=stu, stv=stv)
		usr06, vsr06 = winds.sr_wind(prof, pbot=sfc, ptop=p6km, stu=stu, stv=stv)
		usr13, vsr13 = winds.sr_wind(prof, pbot=p1km, ptop=p3km, stu=stu, stv=stv)
		usr36, vsr36 = winds.sr_wind(prof, pbot=p3km, ptop=p6km, stu=stu, stv=stv)
		Usr01 = utils.mag(usr01, vsr01)
		Usr03 = utils.mag(usr03, vsr03)
		Usr06 = utils.mag(usr06, vsr06)
		Usr13 = utils.mag(usr13, vsr13)
		Usr36 = utils.mag(usr36, vsr36)
		#Helicity
		srhe = abs(winds.helicity(prof, ebot_hgt, etop_hgt, stu=stu, stv=stv)[0])
		srh01 = abs(winds.helicity(prof, 0, 1000, stu=stu, stv=stv)[0])
		srh03 = abs(winds.helicity(prof, 0, 3000, stu=stu, stv=stv)[0])
		srh06 = abs(winds.helicity(prof, 0, 6000, stu=stu, stv=stv)[0])
		#Effective bulk wind shear (diff)
		ebwd = winds.wind_shear(prof, pbot=ebotp, ptop=etopp) 
		prof.ebwd = ebwd
		ebwd = utils.mag(ebwd[0],ebwd[1])
		#Thermodynamic
		try:
			rhmin01 = prof.relh[(prof.hght >= 0) & (prof.hght <= 1000)].min()
		except:
			rhmin01 = prof.relh[0]
		rhmin03 = prof.relh[(prof.hght >= 0) & (prof.hght <= 3000)].min()
		rhmin06 = prof.relh[(prof.hght >= 0) & (prof.hght <= 6000)].min()
		rhmin13 = prof.relh[(prof.hght >= 1000) & (prof.hght <= 3000)].min()
		rhmin36 = prof.relh[(prof.hght >= 3000) & (prof.hght <= 6000)].min()
			#Subcloud layer is below the mixed layer parcel lcl. If the mixed layer parcel lcl is
			# below the first height layer, than let the subcloud rh equal the lowest rh
		try:
			rhminsubcloud = prof.relh[(prof.hght >= 0) & (prof.hght <= ml_pcl.lclhght)].min()
		except:
			rhminsubcloud = prof.relh[0]
		qmean01 = params.mean_mixratio(prof, pbot = sfc, ptop = p1km)
		qmean03 = params.mean_mixratio(prof, pbot = sfc, ptop = p3km)
		qmean06 = params.mean_mixratio(prof, pbot = sfc, ptop = p6km)
		qmean13 = params.mean_mixratio(prof, pbot = p1km, ptop = p3km)
		qmean36 = params.mean_mixratio(prof, pbot = p3km, ptop = p6km)
		qmeansubcloud = params.mean_mixratio(prof, pbot = sfc, ptop = pmllcl)
		q_melting = params.mean_mixratio(prof, pbot=pmelting_hgt, ptop=pmelting_hgt)
		q1 = params.mean_mixratio(prof, pbot=p1km, ptop=p1km)
		q3 = params.mean_mixratio(prof, pbot=p3km, ptop=p3km)
		q6 = params.mean_mixratio(prof, pbot=p6km, ptop=p6km)
		lr_freezing = params.lapse_rate(prof, lower = sfc, upper = pmelting_hgt)
		lr01 = params.lapse_rate(prof, lower = sfc, upper = p1km)
		lr03 = params.lapse_rate(prof, lower = sfc, upper = p3km)
		lr13 = params.lapse_rate(prof, lower = p1km, upper = p3km)
		lr36 = params.lapse_rate(prof, lower = p3km, upper = p6km)
		pwat = params.precip_water(prof)
		v_totals = params.v_totals(prof)
		c_totals = params.c_totals(prof)
		t_totals = c_totals + v_totals
		Rq = qmean01 / 12.
		if Rq > 1:
			Rq = 1
		dcape = params.dcape(prof)[0]
		if dcape < 0:
			dcape = 0
		#Composite
		stp_fixed = params.stp_fixed(sb_pcl.bplus, sb_pcl.lclhght, srh01, s06)
		windex = 5. * np.power((melting_hgt/1000.)*Rq*(np.power(lr_freezing,2)-30.+qmean01-2.*q_melting),0.5) 
			#WINDEX UNDEFINED FOR HIGHLY STABLE CONDITIONS
		if np.isnan(windex):
			windex = 0

		#Fill output
		try:
			#Thermodynamic
			output[i,np.where(param=="ml_cape")[0][0]] = ml_pcl.bplus
			output[i,np.where(param=="mu_cape")[0][0]] = mu_pcl.bplus
			output[i,np.where(param=="sb_cape")[0][0]] = sb_pcl.bplus
			output[i,np.where(param=="eff_cape")[0][0]] = eff_pcl.bplus
			output[i,np.where(param=="ml_cin")[0][0]] = abs(ml_pcl.bminus)
			output[i,np.where(param=="mu_cin")[0][0]] = abs(mu_pcl.bminus)
			output[i,np.where(param=="sb_cin")[0][0]] = abs(sb_pcl.bminus)
			output[i,np.where(param=="eff_cin")[0][0]] = abs(eff_pcl.bminus)
			output[i,np.where(param=="ml_lcl")[0][0]] = ml_pcl.lclhght
			output[i,np.where(param=="mu_lcl")[0][0]] = mu_pcl.lclhght
			output[i,np.where(param=="sb_lcl")[0][0]] = sb_pcl.lclhght
			output[i,np.where(param=="eff_lcl")[0][0]] = eff_pcl.lclhght
			output[i,np.where(param=="dcape")[0][0]] = dcape
			output[i,np.where(param=="lr01")[0][0]] = lr01
			output[i,np.where(param=="lr03")[0][0]] = lr03
			output[i,np.where(param=="lr13")[0][0]] = lr13
			output[i,np.where(param=="lr36")[0][0]] = lr36
			output[i,np.where(param=="lr_freezing")[0][0]] = lr_freezing
			output[i,np.where(param=="mhgt")[0][0]] = melting_hgt
			output[i,np.where(param=="el")[0][0]] = mu_pcl.elhght
			output[i,np.where(param=="qmean01")[0][0]] = qmean01
			output[i,np.where(param=="qmean03")[0][0]] = qmean03
			output[i,np.where(param=="qmean06")[0][0]] = qmean06
			output[i,np.where(param=="qmean13")[0][0]] = qmean13
			output[i,np.where(param=="qmean36")[0][0]] = qmean36
			output[i,np.where(param=="qmeansubcloud")[0][0]] = qmeansubcloud
			output[i,np.where(param=="q_melting")[0][0]] = q_melting
			output[i,np.where(param=="q1")[0][0]] = q1
			output[i,np.where(param=="q3")[0][0]] = q3
			output[i,np.where(param=="q6")[0][0]] = q6
			output[i,np.where(param=="rhmin01")[0][0]] = rhmin01
			output[i,np.where(param=="rhmin03")[0][0]] = rhmin03
			output[i,np.where(param=="rhmin06")[0][0]] = rhmin06
			output[i,np.where(param=="rhmin13")[0][0]] = rhmin13
			output[i,np.where(param=="rhmin36")[0][0]] = rhmin36
			output[i,np.where(param=="rhminsubcloud")[0][0]] = rhminsubcloud
			output[i,np.where(param=="v_totals")[0][0]] = v_totals
			output[i,np.where(param=="c_totals")[0][0]] = c_totals
			output[i,np.where(param=="t_totals")[0][0]] = t_totals
			output[i,np.where(param=="pwat")[0][0]] = pwat
			#From model convection scheme (available for ERA-Interim only)
			if model == "erai":
				output[i,np.where(param=="cp")[0][0]] = cp_chunk[i]
				output[i,np.where(param=="cape")[0][0]] = cape_chunk[i]
				output[i,np.where(param=="cape*s06")[0][0]] = \
					cape_chunk[i] * np.power(utils.KTS2MS(s06), 1.67)
				output[i,np.where(param=="dcp2")[0][0]] = \
					(dcape/980.) * (cape_chunk[i]/2000.) * (utils.KTS2MS(s06) / 20.) * \
					(utils.KTS2MS(Umean06) / 16.)
			#Winds
			output[i,np.where(param=="srhe")[0][0]] = \
				srhe  
			output[i,np.where(param=="srh01")[0][0]] = \
				srh01  
			output[i,np.where(param=="srh03")[0][0]] = \
				srh03 
			output[i,np.where(param=="srh06")[0][0]] = \
				srh06 
			output[i,np.where(param=="ebwd")[0][0]] = \
				utils.KTS2MS(ebwd)
			output[i,np.where(param=="s01")[0][0]] = \
				utils.KTS2MS(s01)
			output[i,np.where(param=="s03")[0][0]] = \
				utils.KTS2MS(s03)
			output[i,np.where(param=="s06")[0][0]] = \
				utils.KTS2MS(s06)
			output[i,np.where(param=="s13")[0][0]] = \
				utils.KTS2MS(s13)
			output[i,np.where(param=="s36")[0][0]] = \
				utils.KTS2MS(s36)
			output[i,np.where(param=="scld")[0][0]] = \
				utils.KTS2MS(scld)
			output[i,np.where(param=="Umean06")[0][0]] = \
				utils.KTS2MS(Umean06)  
			output[i,np.where(param=="Umean800_600")[0][0]] = \
				utils.KTS2MS(Umean800_600)  
			output[i,np.where(param=="U500")[0][0]] = \
				utils.KTS2MS(U500)  
			output[i,np.where(param=="U1")[0][0]] = \
				utils.KTS2MS(U1)  
			output[i,np.where(param=="U3")[0][0]] = \
				utils.KTS2MS(U3)  
			output[i,np.where(param=="U6")[0][0]] = \
				utils.KTS2MS(U6)  
			output[i,np.where(param=="Ust")[0][0]] = \
				utils.KTS2MS(Ust)  
			output[i,np.where(param=="Usr01")[0][0]] = \
				utils.KTS2MS(Usr01)  
			output[i,np.where(param=="Usr03")[0][0]] = \
				utils.KTS2MS(Usr03)  
			output[i,np.where(param=="Usr06")[0][0]] = \
				utils.KTS2MS(Usr06)  
			output[i,np.where(param=="Usr13")[0][0]] = \
				utils.KTS2MS(Usr13)  
			output[i,np.where(param=="Usr36")[0][0]] = \
				utils.KTS2MS(Usr36)  
			output[i,np.where(param=="U10")[0][0]] = \
				utils.KTS2MS(utils.mag(uas_chunk[i],vas_chunk[i]))
			output[i,np.where(param=="Uwindinf")[0][0]] = \
				utils.KTS2MS(Uwindinf)
			output[i,np.where(param=="Umeanwindinf")[0][0]] = \
				utils.KTS2MS(Umeanwindinf)
			output[i,np.where(param=="wg10")[0][0]] = wg10_chunk[i]
			#Wind Composite parameters
			output[i,np.where(param=="dmgwind")[0][0]] = \
				(dcape/800.)* (utils.KTS2MS(Uwindinf) / 8.)
			output[i,np.where(param=="convgust")[0][0]] = \
				utils.KTS2MS(Umean800_600) + 2 * np.sqrt(dcape)
			output[i,np.where(param=="ducs6")[0][0]] = \
				(utils.KTS2MS(Umean800_600) + 2 * np.sqrt(dcape)) / 30. \
				* ((ml_pcl.bplus * np.power(utils.KTS2MS(s06), 1.67)) / 20000.)
			output[i,np.where(param=="dcp")[0][0]] = \
				(dcape/980.) * (ml_pcl.bplus/2000.) * (utils.KTS2MS(s06) / 20.) * \
				(utils.KTS2MS(Umean06) / 16.)
			output[i,np.where(param=="windex")[0][0]] = \
				windex
			output[i,np.where(param=="gustex")[0][0]] = \
				(0.5 * windex) + (0.5 * utils.KTS2MS(U500))
			output[i,np.where(param=="gustex2")[0][0]] = \
				(0.5 * windex) + (0.5 * utils.KTS2MS(Umean06))
			output[i,np.where(param=="gustex3")[0][0]] = \
				(((0.5 * windex) + (0.5 * utils.KTS2MS(Umean06))) / 30.) * \
				((ml_pcl.bplus * np.power(utils.KTS2MS(s06), 1.67)) / 20000.)
			#Other composite parameters
			output[i,np.where(param=="stp_cin")[0][0]] = params.stp_cin( \
				ml_pcl.bplus, srhe, utils.KTS2MS(ebwd), ml_pcl.lclhght, ml_pcl.bminus)
			output[i,np.where(param=="stp_fixed")[0][0]] = \
				stp_fixed
			output[i,np.where(param=="scp")[0][0]] = params.scp( \
				mu_pcl.bplus, srhe, utils.KTS2MS(ebwd))
			output[i,np.where(param=="ship")[0][0]] = params.ship( \
				prof, mupcl=mu_pcl, srh06=srh06)
			output[i,np.where(param=="mlcape*s06")[0][0]] = \
				ml_pcl.bplus * np.power(utils.KTS2MS(s06), 1.67)
			output[i,np.where(param=="mucape*s06")[0][0]] = \
				mu_pcl.bplus * np.power(utils.KTS2MS(s06), 1.67)
			output[i,np.where(param=="eff_sherb")[0][0]] = \
				params.sherb(prof, effective=True, ebottom=ebotp, etop=etopp, mupcl=mu_pcl)
			output[i,np.where(param=="sherb")[0][0]] = \
				params.sherb(prof, effective=False)
			output[i,np.where(param=="wndg")[0][0]] = \
				params.wndg(prof, mlpcl=ml_pcl)
			output[i,np.where(param=="mburst")[0][0]] = \
				params.mburst(prof, sb_pcl, lr03, dcape, v_totals, pwat)
			output[i,np.where(param=="sweat")[0][0]] = \
				params.sweat(prof)
				
		except:
			raise ValueError("\nMAKE SURE THAT OUTPUT PARAMETERS MATCH PARAMETER LIST\n")

#----------------------------------------------------------------------------------------------------------------

	#Print diagnostics
	if rank == 0:
		print("TOTAL (LAND) POINTS: %s" %(ta.shape[0]))
		print("CHUNKSIZE: %s" %(ua_chunk.shape,))
		print("Time taken for SHARPPy on processor 1: %s" %(dt.datetime.now() - start), )
		print("Time taken for each element: %s" %((dt.datetime.now() - start)/float(ua_chunk.shape[0])), )

	#Gather output data together to root node
	comm.Gatherv(output, \
		[output_data, split_sizes_output, displacements_output, MPI.DOUBLE], \
		root=0)

	#Reshape data and save. For effective layer variables (given by effective_layer_params, see line ~143), 
	# which are undefined when there is no surface cape, replace masked values with zeros
	if rank == 0:
		param_out = []
		for param_name in param:
			#Extract data for land points (which is 1d) and replace masked elements with zeros for 
			# effective layer parameters
			temp_data = output_data[:,np.where(param==param_name)[0][0]]
			if param_name in effective_layer_params:
				temp_data[np.isnan(temp_data)] = 0.
			#Reshape back into a 3d array (time x lon x lat) on full grid (land and ocean points)
			output_reshaped = np.zeros((orig_length))
			output_reshaped[:] = np.nan
			output_reshaped[lsm_orig==1] =  temp_data
			output_reshaped = output_reshaped.reshape((orig_shape[0],orig_shape[2],orig_shape[3]))
			param_out.append(output_reshaped)

		save_netcdf(region, model, out_name, date_list, lat, lon, param, param_out)

