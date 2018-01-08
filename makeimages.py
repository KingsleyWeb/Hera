import glob
#run this from casa for now
def imgtopng(fold):
    """makes png images from img for easy viewing"""
    fnew=str.replace(fold,".uv.img.image","") + ".png"
    imview(raster=fold, out=fnew)
    return fnew
    
def imgtofits(fold):
    """makes fits images from img for easy viewing"""
    fnew=str.replace(fold,".uv.img.image","") + ".fits"
    exportfits(imagename=fold, fitsimage=fnew)
    return fnew
    
flist=[imgtofits(f) for f in glob.glob("*.img.image")]
print flist
flist=[imgtopng(f) for f in glob.glob("*.img.image")]
print flist
