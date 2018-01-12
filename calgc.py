# This is a RECIPE script for CASA. See Nikolic, Small & Kettenis 2017
# for RECIPE.
import numpy

import sys; sys.path.append("/home/bnikolic/n/recipe/")
import recipe; from recipe.casatasks import *;

recipe.repo.REPODIR="/bigfast/temp1/repo/"
recipe.casatasks.TRACEV=1

GCCleanMask='ellipse[[17h45m00.0s,-29d00m00.00s ], [ 11deg, 4deg ] , 30deg]'
ingc="/home/bnikolic/n/casata/test/hera/casarun/GC.cl"
invis="/bigfast/temp1/mss/zen.2458042.12552.xx.HH.ms"

def getflaggedantsi(ct):
    "Show which anntennas have calibrations flagged"
    tb=casac.casac.table()
    tb.open(ct)
    print tb.getcol("ANTENNA1")[tb.getcol('FLAG')[0][0]]
    tb.done()

def flaggedants(v, ct):
    """Get antenna numbers for flagged  antennas"""
    tb=casac.casac.table()
    tb.open(os.path.join(v,"ANTENNA"))
    n=tb.getcol("NAME")
    tb.close()
    tb.open(ct)
    nn=tb.getcol("ANTENNA1")
    f=tb.getcol('FLAG')[0][0]
    tb.close()
    tb.done()    
    return nn[numpy.logical_and(f==True, n != '' )]

def viewimg(i, s="", c="image"):
    os.popen2("DISPLAY=\":0\" /data/p/casa-release-5.1.0-74.el7/lib/casa/bin/casaviewer %s/img%s.%s" %
              (i, s, c))

def viewms(i):
    os.popen2("DISPLAY=\":0\" /data/p/casa-release-5.1.0-74.el7/lib/casa/bin/casaplotms vis=%s/vis" %
              (i, ))    
    

f1=ft(invis, complist=ingc, usescratch=True)


# The default for argument "interp" gets flipped randomly so best to
# explicitly specify. Could be fixed-up behind scenes in recipe?
K=gaincal(f1,
          gaintype='K', refant="11", interp='linear')
        
G=gaincal(f1,
          gaintable=[K],
          gaintype='G',
          calmode='ap', interp='linear',
          refant="11")

# NB: once the calibration is applied the antennas with flagged
# solutions remain flagged. 
f2=applycal(f1, gaintable=[K, G] , interp='linear')        

# Don't split; splitting truncates the validity of the model image,
# the FT step then does not seem to work particularly well
f3=f2

# First clean, to setup a very simple model for the GC
ooorig=clean(vis=f3,
         niter=50,
         weighting='briggs',
         robust=0,
         imsize=[1024,1024],
         cell=['250arcsec'],
         mode='mfs',
         nterms=1,
         spw='0:150~900',
         reffreq='120MHz',
         #spw='0:150~700',
         mask=GCCleanMask)

def iterselfcal(visin, img, niter, mask,
                dobandpass=False):
    """Make one iteration of the self cal loop

    :param dobandpass: Do a bandpass calibration ?

    """

    # Now back to the original vis for the calibration. NB. use the
    # *model* output from previous here
    f33=ft(visin,
           model=os.path.join(img, "img.model"),
           usescratch=True)
    ctl=[]
    K2=gaincal(f33,
               gaintype='K',
               refant="11",
               interp='linear')
    ctl.append(K2)

    G2=gaincal(f33,
               gaintype='G',
               gaintable=[K2],           
               calmode='ap',
               interp='linear',
               refant="11",
               minsnr=3.01)
    ctl.append(G2)

    if dobandpass:
        B2=bandpass(f33, solnorm=False, bandtype="B",
                    gaintable=ctl)
        ctl.append(B2)
        

    f33=applycal(f33,
                 gaintable=ctl,
                 interp='linear')        
    # Reclean
    oo=clean(vis=f33,
             niter=niter,
             weighting='briggs',
             robust=0,
             imsize=[1024,1024],
             cell=['250arcsec'],
             mode='mfs',
             nterms=1,
             spw='0:150~900',
             reffreq='120MHz',
             #spw='0:150~700',
             mask=mask)
    return oo, ctl

oo1,GG1=iterselfcal(f1, ooorig, 500, GCCleanMask)
oo11,GG2=iterselfcal(f1, oo1, 5000, GCCleanMask)
oo2,GG3=iterselfcal(f1, oo1, 500, GCCleanMask,
                dobandpass=True)
oo3,GG4=iterselfcal(f1, oo2, 5000,
                None,
                dobandpass=True)
oo3withmask,GT=iterselfcal(f1, oo2,
                           5000,
                           GCCleanMask,
                           dobandpass=True)

def selfcal21h(visin, 
               niter,
               cal=[],
               dobandpass=False):
    """Self cal on the 21h field. Unfortunately I've reversed the order of
    clean vs calibration relative to the GC self cal iteration
    (reason: focus was more on the number of flagged gaincal solutions
    rather than the images)
    """

    if cal != []:
        visin=applycal(visin,
                       gaintable=cal,
                       interp='linear')
    # Note the use of multiple phase centres. Found this is
    # esssential, widefield CASA imaging just seems confused with a
    # ~70deg zenith angle of Cyg A. Facetting and other widefield
    # modes even worse, but multiple phase centres seem to work fine.
    oo2comb=clean(visin,
                  niter=niter,
                  weighting='briggs',
                  robust=0,
                  imsize=[[512,512], [512,512]],
                  cell=['220arcsec'],
                  mode='mfs',
                  nterms=1,
                  spw='0:150~900',
                  phasecenter=["J2000 21h00m00s -26d0m0s", #NB
                               "J2000 20h00m99s 41d0m0s"])
    # Insert both models images into the visibility model column
    f1=ft(vis21h,
          model=[os.path.join(oo2comb, "img0.model"),
                 os.path.join(oo2comb, "img0.model")],
          usescratch=True)
    newcal=[]
    K4=gaincal(f1,
               gaintype='K',
               refant="11",
               gaintable=cal,
               interp='linear')
    newcal.append(K4)

    G4=gaincal(f1,
               gaintable=GT+newcal,
               gaintype='G',
               calmode='ap',
               refant="11",
               interp='linear',
               minsnr=3.)
    newcal.append(G4)    

    if dobandpass:
        B2=bandpass(f1,
                    solnorm=False,
                    bandtype="B",
                    gaintable=GT+newcal)
        newcal.append(B2)
    return oo2comb, newcal
            

vis21h="/bigfast/temp1/mss/zen.2458042.24482.xx.HH.ms"    

o1,c1=selfcal21h(vis21h, 
                 100,
                 cal=GT,
                 dobandpass=False)

o2,c2=selfcal21h(vis21h, 
                 1000,
                 cal=GT+c1,
                 dobandpass=False)

o3,c3=selfcal21h(vis21h, 
                 1000,
                 cal=GT+c2,
                 dobandpass=True)

o4,c4=selfcal21h(vis21h, 
                 5000,
                 cal=GT+c3,
                 dobandpass=True)

o5,c5=selfcal21h(vis21h, 
                 5000,
                 cal=GT+c4,
                 dobandpass=True)



