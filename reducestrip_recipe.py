import os
import glob
from casarecipe import casatasks as c
from casarecipe import repo
import casac
import casa
import shutil
import pyuvdata

#File location specification
DataDir="/rds/project/bn204/rds-bn204-asterics/HERA/data"
c.repo.REPODIR="/rds/project/bn204/rds-bn204-asterics/repo/strip"

#processing specification
Pol="xx" #or "yy", etc
ProcessData=False
MakePNG=False
RefAnt="53" #as a string

#Callibration source specification
CalTarget="J2000 17h45m40.0409s -29d0m28.118s"
CalCleanMask='ellipse[[17h45m00.0s,-29d00m00.00s ], [ 11deg, 4deg ] , 30deg]'
CalTime=12552
CalInDay=2458042

#Target specification
Target="J2000 17h45m40.0409s -29d0m28.118s"
TargetCleanMask="box[[128pix,128pix],[896pix,896pix]]"
InTimes = [13298] 
InDay=2458042

#string builders for various filenames
#InData = [ os.path.join(DataDir, str(InDay), Pol,"zen." + str(InDay)+"." + str(x) + "." + str(Pol) + ".HH.uv") for x in InTimes]

InData = glob.glob(os.path.join(DataDir,str(CalInDay),Pol,"*.uv")) #process the whole directory
print InData
CalFilename=os.path.join(DataDir,str(CalInDay),Pol,"zen." + str(CalInDay)+"." + str(CalTime) + "." + str(Pol) + ".HH.uv")
print CalFilename
###############################
def mkuvfits(fin):
	hh=c.hf(mkuvfits, fin)
	mm=repo.get(hh)
	if mm:
		c.trc( "[Cached]", "mkuvfits", fin)
		return mm
	else:
		c.trc( "[Eval] ", "mkuvfits", fin, " -> ", hh)
		UV = pyuvdata.UVData()
		UV.read_miriad(fin,'miriad')
		UV.phase_to_time(UV.time_array[0])
		tempf=repo.mktemp()
		os.remove(tempf)
		UV.write_uvfits(tempf,'uvfits')
	if not os.path.exists(tempf):
		raise RuntimeError("No output produced by mkuvfits !")
	return repo.put(tempf, hh)


def mkinitmodel(tgt,modelname):
	""" Initial model: just a point source in specified direction"""
	if not os.path.exists(modelname):
		cl=casac.casac.componentlist()
		cl.addcomponent(flux=1.0,
							fluxunit='Jy',
							shape='point',
							dir=str(tgt))            
		cl.rename(modelname)
		cl.close()
	return modelname
	
def copyoutput(dsin,dsout,extension):
	"""copy output from dsin using dsout as directory names"""
	for i,f in enumerate(dsin):
		fin=os.path.join(f,extension)
		fout=os.path.split(dsout[i])[-1]+"."+extension
		if os.path.exists(fout):
			shutil.rmtree(fout)
		shutil.copytree(fin,fout)
	
###############################
def main():
	cl=mkinitmodel(CalTarget,os.path.join(c.repo.REPODIR,"CL.cal"))
	#for cal data
	cfits=mkuvfits(CalFilename)
	cms=c.importuvfits(cfits)
	cmsf=c.flagdata(cms, autocorr=True)
	cmsfr=c.fixvis(cmsf,phasecenter=CalTarget)
	cmsfrm=c.ft(cmsfr,complist=cl,usescratch=True)
	K=c.gaincal(cmsfrm, gaintype="K", refant=RefAnt)
	G=c.gaincal(cmsfrm, gaintable=[K], calmode="ap", refant=RefAnt)
	
	#image cal for sanity
	cmsfrmc=c.applycal(cmsfrm, gaintable=[K, G])
	cmsfrmcs=c.split(cmsfrmc,datacolumn="corrected")
	ci=c.clean(vis=cmsfrmcs,
				niter=500,
				weighting='briggs',
				robust=0,
				imsize=[1024,1024],
				cell=['250arcsec'],
				mode='mfs',
				nterms=1,
				spw='0:150~900',
				reffreq='120MHz',
				mask=CalCleanMask)

	#for product data
	dfits=[mkuvfits(f) for f in InData]
	dms=[c.importuvfits(f) for f in dfits]
	dmsf=[c.flagdata(f, autocorr=True) for f in dms]
	dmsfc=[c.applycal(f, gaintable=[K, G]) for f in dmsf]
	dmsfcs=[c.split(f,datacolumn="corrected") for f in dmsfc]

	#imgaing
	msi=[c.clean(vis=f,
				niter=500,
				weighting='briggs',
				robust=0,
				imsize=[1024,1024],
				cell=['250arcsec'],
				mode='mfs',
				nterms=1,
				spw='0:150~900',
				reffreq='120MHz',
				mask=TargetCleanMask) for f in dmsfcs]	
	
	#save the output images to something sensible
	copyoutput(msi,InData,"img.image")
      
if ProcessData: main()

