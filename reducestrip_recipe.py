import os
import glob
from casarecipe import casatasks as c
import casac
import casa
import shutil

#File location specification
DataDir="/mnt/ktg500/HeraIDR1"
c.repo.REPODIR="/mnt/ktg500/repo"

#processing specification
Pol="xx" #or "yy", etc
ProcessData=True
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
InTimes = [12552,13298,14043] 
InDay=2458042

#string builders for various filenames
InData = [ "zen." + str(InDay)+"." + str(x) + "." + str(Pol) + ".HH.uvfits" for x in InTimes]
#InData = glob.glob(os.pahth.join(Datadir,"*.uvfits")) #process the whole directory
CalFilename="zen." + str(CalInDay)+"." + str(CalTime) + "." + str(Pol) + ".HH.uvfits"

###############################
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
	cms=c.importuvfits(CalFilename)
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
	ms=[c.importuvfits(f) for f in InData]
	msf=[c.flagdata(f, autocorr=True) for f in ms]
	msfc=[c.applycal(f, gaintable=[K, G]) for f in msf]
	msfcs=[c.split(f,datacolumn="corrected") for f in msfc]

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
				mask=TargetCleanMask) for f in msfcs]	
	
	#save the output images to something sensible
	copyoutput(msi,InData,"img.image")
      
if ProcessData: main()

