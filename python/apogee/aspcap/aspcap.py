# encoding: utf-8
#
# @Author: Jon Holtzman
# @Date: March 2018
# @Filename: synth.py
# @License: BSD 3-Clause
# @Copyright: Jon Holtzman

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import matplotlib
matplotlib.use('Agg')

import numpy as np
import glob
import os
import pdb
from shutil import copyfile
import subprocess
import scipy.ndimage.filters
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.io import ascii
#from holtz.tools import struct
from tools import plots
from tools import match
from tools import html
from apogee.utils import apload
from apogee.utils import bitmask
from apogee.utils import spectra
from apogee.speclib import isochrones
try: from apogee.aspcap import ferre
except: pass

def params() :
    '''
    Define the order of the parameter arrays, with the associated FERRE names, tag names, and flag names
    '''
    tagnames=np.array(['TEFF','LOGG','LOGVMICRO','M_H','C_M','N_M','ALPHA_M','LGVSINI','PARAM_O'])
    flagnames=np.array(['TEFF','LOGG','VMICRO','M_H','C_M','N_M','ALPHA_M','VSINI','O'])
    params=np.array(['TEFF','LOGG','LOG10VDOP','METALS','C','N','O Mg Si S Ca Ti','LGVSINI','O'])
    return params,tagnames,flagnames

def elems(nelem=0) :
    '''
    Define the order of the element arrays
    '''

    elems=['C','CI','N','O','Na','Mg','Al','Si','P','S','K','Ca','Ti','TiII','V','Cr','Mn','Fe','Co','Ni','Cu','Ge','Rb','Ce','Nd','Yb']
    #return,['C','N','O','Na','Mg','Al','Si','S','K','Ca','Ti','V','Mn','Fe','Ni','Nd']
    #return,['C','N','O','Na','Mg','Al','Si','S','K','Ca','Ti','V','Mn','Fe','Ni']
    elemtoh=[0,0,0,0,1,0,1,0,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1] #0,0,0,0,0,0,0,0,0]
    tagnames=[]
    elemfitnames=[]
    for i in range(len(elems) ) :
        if elemtoh[i] :
            tagnames.append(elems[i]+'_Fe')
            elemfitnames.append('['+elems[i]+'/Fe]')
        else :
            tagnames.append(elems[i]+'_M')
            elemfitnames.append('['+elems[i]+'/M]')
    return elems,elemtoh,tagnames,elemfitnames

logw0=4.179
dlogw=6.e-6
nw_apStar=8575
def apStarWave() :
    """ Returns apStar wavelengths
    """
    return 10.**(logw0+np.arange(nw_apStar)*dlogw)

logw0_chip=np.array([4.180476,4.200510,4.217064])
nw_chip=np.array([3028,2495,1991])
def gridWave() :
    """ Returns aspcap grid wavelengths
    """
    return [10.**(logw0_chip[0]+np.arange(nw_chip[0])*dlogw),
            10.**(logw0_chip[1]+np.arange(nw_chip[1])*dlogw),
            10.**(logw0_chip[2]+np.arange(nw_chip[2])*dlogw)]

def gridPix(apStar=True) :
    """ Returns chip pixel ranges in apStar or aspcap grid
    """
    if apStar :
        w=np.log10(apStarWave())
        s1 = np.where(np.isclose(w,logw0_chip[0],rtol=0.))[0][0]
        s2 = np.where(np.isclose(w,logw0_chip[1],rtol=0.))[0][0]
        s3 = np.where(np.isclose(w,logw0_chip[2],rtol=0.))[0][0]
        e1 = np.where(np.isclose(w,logw0_chip[0]+nw_chip[0]*dlogw,rtol=0.))[0][0]
        e2 = np.where(np.isclose(w,logw0_chip[1]+nw_chip[1]*dlogw,rtol=0.))[0][0]
        e3 = np.where(np.isclose(w,logw0_chip[2]+nw_chip[2]*dlogw,rtol=0.))[0][0]
        return [[s1,e1],[s2,e2],[s3,e3]]
    else :
        return [[0,nw_chip[0]],[nw_chip[0],nw_chip[0]+nw_chip[1]],[nw_chip[0]+nw_chip[1],nw_chip[0]+nw_chip[1]+nw_chip[2]]]

def aspcap2apStar(aspcap):
    """ from input aspcap spectrum on aspcap grid, return spectrum on apStar grid 
    """
    apstar=np.zeros(nw_apStar)
    pix_out=gridPix()
    pix_in=gridPix(apStar=False)
    for pin,pout in zip(pix_in,pix_out) :
        apstar[pout[0]:pout[1]] = aspcap[pin[0]:pin[1]]
    return apstar

def apStar2aspcap(apstar):
    """ from input aspcap spectrum on aspcap grid, return spectrum on apStar grid 
    """
    aspcap=np.zeros(nw_chip.sum())
    pix_out=gridPix()
    pix_in=gridPix(apStar=False)
    for pin,pout in zip(pix_in,pix_out) :
        aspcap[pin[0]:pin[1]] = apstar[pout[0]:pout[1]] 
    return aspcap

def readstars(starlist,libpar) :
    '''
    Runs stars in starlist through FERRE using libpar
    '''
    for star in starlist :
        spec,err=readstar(star)
        cont=cont_normalize(spec)

def getparams(name,lib,coarse=None,n=None) :

    objs=ascii.read(name+'.ipf')['col1']
    if n is not None : objs = objs[0:n]

    # if we have a coarse library, run FERRE with it first
    #   to get starting guesses
    if coarse is not None :
        l=ferre.rdlibhead(coarse+'.hdr')[0]
        link(name+'.obs',name+'_coarse.obs')
        link(name+'.err',name+'_coarse.err')
        ferre.writeipf(name+'_coarse',coarse+'.hdr',objs)
        ferre.writenml(name+'_coarse.nml',name+'_coarse',l,algor=3,renorm=4,obscont=1,ncpus=32,init=1)
        copyfile(name+'_coarse.nml','input.nml')
        subprocess.call(['ferre.x'],shell=False)
        out,outspec,outwave=ferre.read(name+'_coarse',coarse+'.hdr')
        ferre.writeipf(name+'_1',lib+'.hdr',objs,param=out['FPARAM']) 
    else :
        ferre.writeipf(name+'_1',lib+'.hdr',objs)
    l=ferre.rdlibhead(lib+'.hdr')[0]
    ferre.writenml(name+'_1.nml',name+'_1',l,algor=3,renorm=4,obscont=1,ncpus=32,init=1)
    copyfile(name+'_1.nml','input.nml')
    link(name+'.obs',name+'_1.obs')
    link(name+'.err',name+'_1.err')
    subprocess.call(['ferre.x'],shell=False)
    out,outspec,outwave=ferre.read(name+'_1',lib+'.hdr')


def link(src,dest) :
    try :
        os.remove(dest)
    except :
        pass
    os.symlink(src,dest)
   
def elemsens(els=None,plot=None,ylim=[0.1,-0.3],teff=4750,logg=2.,feh=-1.,smooth=None) :
    '''
    Returns and optionally plots wavelength sensitivity to changes in elemental abundances for specified elements from MOOG mini-elem grid
    '''
    elem=fits.open(os.environ['APOGEE_REDUX']+'/speclib/moog/elemsens.fits')
    if els is None :
        els = elems()[0]
    elif type(els) == str :
        els = [els]
    wave=[]
    out=[]
    for el in els :
        for i in range(1,25) :
            card='HDU{:02d}'.format(i)
            try :
              if elem[0].header[card].strip().upper() == el.strip().upper() :
                it=int(round((teff-elem[i].header['CRVAL2'])/elem[i].header['CDELT2']))
                ig=int(round((logg-elem[i].header['CRVAL3'])/elem[i].header['CDELT3']))
                ife=int(round((feh-elem[i].header['CRVAL4'])/elem[i].header['CDELT4']))
                diff=elem[i].data[ife,ig,it,:]
                if smooth is not None:
                    diff=scipy.ndimage.filters.gaussian_filter(diff,smooth)
                wave=elem[i].header['CRVAL1']+np.arange(elem[i].header['NAXIS1'])*elem[i].header['CDELT1']
                if plot is not None:
                    #plot.plot(wave,diff,color='g')
                    plot.plot(wave,diff)
                    plot.set_ylim(ylim[0],ylim[1])
                out.append(diff)
            except: pass
    if len(out) == 1 :
        return wave, out[0]
    else :
        return wave, out

def sensplot(ax=None,offset=0) :
    if ax is None :
        fig,ax=plots.multi(1,2,hspace=0.001,sharex=True)
    els=['O','Mg','Si','S','Ca','Ti','Na','Al','K','P']
    cols=['r','g','b','c','y','m','r','g','b','c']
    ls=['-','-','-','-','-','-',':',':',':',':']
    for i in range(len(els)) :
        w,s=elemsens(els=els[i])
        plots.plotl(ax[0],w,s+offset,label=els[i],color=cols[i],ls=ls[i])
    ax[0].legend(fontsize='small')

    elems=['C','CI','N','O','Na','Mg','Al','Si','P','S','K','Ca','Ti','TiII','V','Cr','Mn','Fe','Co','Ni','Cu','Ge','Ce','Rb','Y','Nd']
    els=['V','Cr','Mn','Co','Ni','Cu','Ge','Ce','Rb','Nd']
    cols=['r','g','b','c','y','m','r','g','b','c']
    ls=['-','-','-','-','-','-',':',':',':',':']
    for i in range(len(els)) :
        w,s=elemsens(els=els[i])
        plots.plotl(ax[1],w,s+offset,label=els[i],color=cols[i],ls=ls[i])
    ax[1].legend(fontsize='small')
    #elems=['C','CI','N','O','Na','Mg','Al','Si','P','S','K','Ca','Ti','TiII','V','Cr','Mn','Fe','Co','Ni','Cu','Ge','Ce','Rb','Y','Nd']
    

def data(str,loc=None) :       
    '''
    Add apogeeObject data to structure
    '''
    add=np.empty(1,dtype=[('RA','f4'),('DEC','f4'),('J','f4'),('H','f4'),('K','f4'),('AK_TARG','f4'),('SFD_EBV','f4')])
    new=struct.add_cols(str,add)
    for i in range(len(str)) :
        name = str['APOGEE_ID'][i]
        print(i, name)
        apogee_id = name.split('.')[0].split('-')[2]
        if loc is None :
            loc = name.split('.')[1].split('_')[0]
        ap=apload.ApLoad()
        s=ap.apStar(loc,apogee_id)
        field=s[0].header['FIELD']
        try :
            obj=fits.open(os.environ['APOGEE_TARGET']+'/apogeeObject/apogeeObject_'+field+'.fits')[1].data
        except :
            obj=fits.open(os.environ['APOGEE_TARGET']+'/apogee2object/apogee2object_'+field+'.fits')[1].data
        j=np.where(obj['APOGEE_ID'] == apogee_id)[0]
        for card in add.dtype.names :
            new[card][i]=obj[card][j]
    return new

def elemmask(el,maskdir='filters_26112015',plot=None,yr=[0,1]) :
    '''
    '''
    mask=np.loadtxt(os.getenv('SPECLIB_DIR')+'/lib/'+maskdir+'/'+el+'.filt') 
    wave=np.loadtxt(os.getenv('SPECLIB_DIR')+'/lib/'+maskdir+'/wave.dat')
    if plot is not None :
        plots.plotl(plot,wave,mask,yr=yr)
    return wave,mask

def intplot(a=None,param='FPARAM',indir='cal',apred='r10',aspcap='t33b',verbose=False) :
    """ Given input structure, plot HR diagram, and enter event loop to mark stars to plot spectra
    """

    load=apload.ApLoad(apred=apred,aspcap=aspcap,verbose=verbose)
    if a is None : a=load.allCal()[1].data

    fig,ax = hr(a,param=param)
    plots.event(fig)
    sf,sa=plots.multi(1,1)
    nplot = 11
    hf,ha=plots.multi(1,nplot,figsize=(8.5,11),hspace=0.2)
    ha2=[]
    for i in range(nplot) : ha2.append(ha[i].twinx())
    print('hit any key near object to plot in HR diagram, q to quit')
    while (1) :
        ret=plots.mark(fig)
        if ret[2] == 'q' : break
        ind=plots._index[0]
        load.settelescope('apo25m')
        try : f=load.aspcapField(a['ALTFIELD'][ind])
        except : f=load.aspcapField(a['FIELD'][ind])
        if f is None :
            load.settelescope('lco25m')
            try : f=load.aspcapField(a['ALTFIELD'][ind])
            except : f=load.aspcapField(a['FIELD'][ind])
        if f is None :
            f=glob.glob(indir+'/*'+a['APOGEE_ID'][plots._index[0]]+'*')
            dir=os.path.dirname(f[0])
            f=glob.glob(dir+'/*aspcapField*.fits')
            f=fits.open(f[0])
        print('f: ',f)
        data=f[1].data
        j=np.where(data['APOGEE_ID'] == a['APOGEE_ID'][plots._index[0]])[0][0]
        sa.cla()
        for i in range(11) : 
            ha[i].cla()
            ha2[i].cla()
            ha[i].set_ylabel('Flux')
            ha2[i].set_ylabel(r'$\chi^2$')
            ha[i].set_ylim(0.5,1.3)
            ha2[i].set_ylim(0.,20.)
        plot(10.**f[3].data['WAVE'][0],f[2].data['SPEC'][j,:],ax=ha,sum=True,color='k')
        plot(10.**f[3].data['WAVE'][0],f[2].data['SPEC_BESTFIT'][j,:],ax=ha,sum=True,color='b')
        chi2 = (f[2].data['SPEC'][j,:]-f[2].data['SPEC_BESTFIT'][j,:])**2/f[2].data['ERR'][j,:]**2
        plot(10.**f[3].data['WAVE'][0],chi2,ax=ha2,sum=True,alpha=0.4)
        plots.plotl(sa,10.**f[3].data['WAVE'][0],f[2].data['SPEC'][j,:])
        plots.plotl(sa,10.**f[3].data['WAVE'][0],f[2].data['SPEC_BESTFIT'][j,:])
        text1=r'ID: {:s} FIELD: {:s} SNR: {:6.1f} $\chi^2$: {:6.1f}'.format(
             data['APOGEE_ID'][j],data['FIELD'][j],data['SNR'][j],data['PARAM_CHI2'][j])
        text2=r'Teff: {:5.0f} logg: {:5.1f} [M/H]: {:5.2f} [$\alpha$/M]: {:5.2f} [C/M]: {:5.2f} [N/M]: {:5.2f}'.format(
             data[param][j,0],data[param][j,1],data[param][j,3],data[param][j,6],data[param][j,4],data[param][j,5])
        sf.suptitle(text1+'\n'+text2)
        hf.suptitle(text1+'\n'+text2)
        plt.draw()
        plt.show()
    plt.close(hf)
    plt.close(sf)
    plt.close(fig)

def hr(a,param='FPARAM',colorbar=False,zt='[M/H]',zr=None,iso=False, hard=None, gridclass=None,xr=[8000,3000],yr=[6,-1],grid=False,contour=False) :
    """ Plot an HR diagram from input structure

        Args:
            all  : structure that includes stellar parameter array with (Teff, logg, ...)
            param : tag to use (default='FPARAM')
            colorbar : show colorbar? (default= False)
    """
    fig,ax = plots.multi(1,1)
    if gridclass is None :
        teff=a[param][:,0]
        logg=a[param][:,1]
    else :
        teff=a['FPARAM_CLASS'][:,gridclass,0]
        logg=a['FPARAM_CLASS'][:,gridclass,1]
    if zt == '[M/H]' : 
        z=a[param][:,3]
        if zr is None : zr=[-2,0.5]
    elif zt == 'chi2' : 
        z=a['PARAM_CHI2']
        if zr is None : zr=[0,10]
    aspcapmask=bitmask.AspcapBitMask()
    starmask=bitmask.StarBitMask()
    bd=np.where( ((a['ASPCAPFLAG']&aspcapmask.badval()) > 0) |
                 ((a['STARFLAG']&starmask.badval()) > 0) ) [0]
    gd=np.where( ((a['ASPCAPFLAG']&aspcapmask.badval()) == 0) &
                 ((a['STARFLAG']&starmask.badval()) == 0) ) [0]
    if contour :
        plots.plotp(ax,teff,logg,xr=xr,yr=yr,
                    xt='Teff',yt='log g',contour=-1)
    else :
        plots.plotc(ax,teff[gd],logg[gd],z[gd],xr=xr,yr=yr,zr=zr,
                    xt='Teff',yt='log g',zt=zt,colorbar=colorbar)
        plots.plotp(ax,teff[bd],logg[bd],color='k',size=2)
    if grid: ax.grid()
    plots._data = a
    if iso:
        colors=['b','g','k','r']
        for i,z in enumerate(['zm20','zm10','zp00','zp05']) :
            isodata=isochrones.read(os.environ['ISOCHRONE_DIR']+'/'+z+'.dat',agerange=[7.99,8.01])
            isochrones.plot(ax,isodata,'teff','logg',color=colors[i],alpha=0.3)
            isodata=isochrones.read(os.environ['ISOCHRONE_DIR']+'/'+z+'.dat',agerange=[9.99,10.01])
            isochrones.plot(ax,isodata,'teff','logg',color=colors[i],alpha=0.3)
    if hard is not None: 
        fig.savefig(hard)
        plt.close()
    return fig,ax

def multihr(a,param='FPARAM',colorbar=False,hard=None,xr=[8000,3000],yr=[6,-1]) :
    """ Series of HR diagram plots, color-coded by different quantities
    """
    fig,ax = plots.multi(3,3,hspace=0.001,wspace=0.001,figsize=(8,12))

    aspcapmask=bitmask.AspcapBitMask()
    starmask=bitmask.StarBitMask()
    bd=np.where( ((a['ASPCAPFLAG']&aspcapmask.badval()) > 0) |
                 ((a['STARFLAG']&starmask.badval()) > 0) ) [0]
    gd=np.where( ((a['ASPCAPFLAG']&aspcapmask.badval()) == 0) &
                 ((a['STARFLAG']&starmask.badval()) == 0) ) [0]

    z=a[param][gd,3]
    zr=[-2,0.5]
    zt='[M/H]'
    plots.plotc(ax[0,0],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',yt='log g',zt=zt,colorbar=colorbar)
    ax[0,0].text(0.05,0.9,zt,transform=ax[0,0].transAxes)

    z=10.**a[param][gd,2]
    zr=[0.3,4]
    zt='vmicro'
    plots.plotc(ax[0,1],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',zt=zt,colorbar=colorbar)
    ax[0,1].text(0.05,0.9,zt,transform=ax[0,1].transAxes)

    z=10.**a[param][gd,7]
    zr=[0,10]
    zt='vrot'
    plots.plotc(ax[0,2],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',zt=zt,colorbar=colorbar)
    ax[0,2].text(0.05,0.9,zt,transform=ax[0,2].transAxes)

    z=a[param][gd,4]
    zr=[-0.5,0.5]
    zt='[C/M]'
    plots.plotc(ax[1,0],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',yt='log g',zt=zt,colorbar=colorbar)
    ax[1,0].text(0.05,0.9,zt,transform=ax[1,0].transAxes)

    z=a[param][gd,5]
    zr=[-0.5,0.5]
    zt='[N/M]'
    plots.plotc(ax[1,1],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',zt=zt,colorbar=colorbar)
    ax[1,1].text(0.05,0.9,zt,transform=ax[1,1].transAxes)

    z=a[param][gd,4]-a[param][gd,5]
    zr=[-0.5,0.5]
    zt='[C/N]'
    plots.plotc(ax[1,2],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',zt=zt,colorbar=colorbar)
    ax[1,2].text(0.05,0.9,zt,transform=ax[1,2].transAxes)

    z=a[param][gd,6]
    zr=[-1,1.0]
    zt=r'[$\alpha$/M]'
    plots.plotc(ax[2,0],a[param][gd,0],a[param][gd,1],z,xr=xr,yr=yr,zr=zr,
                xt='Teff',yt='log g',zt=zt,colorbar=colorbar)
    ax[2,0].text(0.05,0.9,zt,transform=ax[2,0].transAxes)

    z=np.log10(a['PARAM_CHI2'])
    zr=[0,2]
    zt='log(CHI2)'
    plots.plotc(ax[2,1],a[param][gd,0],a[param][gd,1],z[gd],xr=xr,yr=yr,zr=zr,
                xt='Teff',zt=zt,colorbar=colorbar)
    ax[2,1].text(0.05,0.9,zt,transform=ax[2,1].transAxes)

    z=a['MEANFIB']
    zr=[0,300]
    zt='MEANFIB'
    plots.plotc(ax[2,2],a[param][gd,0],a[param][gd,1],z[gd],xr=xr,yr=yr,zr=zr,
                xt='Teff',zt=zt,colorbar=colorbar)
    ax[2,2].text(0.05,0.9,zt,transform=ax[2,2].transAxes)

    if hard is not None: 
        fig.savefig(hard)
        plt.close()

#def hrclass(a) :
#    fig,ax=plots.multi(2,3)
#    for class in ['GKg','GKg_O','Mg','Md','GKd','Fd'] :

def plot(wave,spec,color=None,figax=None,ax=None,hard=None,sum=False,title=None,alpha=None,yr=None,lineids=None,multipage=False, refline=None, figsize=(8,11)) :
    """  Multipanel plots of APOGEE spectra
    """
    # set up plots
    if sum : ny=11
    else : ny=10
    if figax is not None : fig,ax=figax
    if ax is None : fig,ax=plots.multi(1,ny,figsize=figsize,hspace=0.2)

    # get line labels if requested
    if lineids is not None :
        file = os.environ['APOGEE_DIR']+'/data/lines/atlas_line_ids_apogee.txt'
        lines = np.loadtxt(file,delimiter=';',dtype={'names' : ('wave','label'), 'formats': ('f4','S24') } )
        lines['wave'] = spectra.airtovac(lines['wave'])

    # plot chunks of 200 A
    for i in range(10) :
        plots.plotl(ax[i],wave,spec,xr=[15000+i*200,15200+i*200],color=color,linewidth=0.3,alpha=alpha,yr=yr)
        ax[i].xaxis.label.set_size(6)
        ax[i].yaxis.label.set_size(6)
        ax[i].tick_params(axis = 'both', which = 'major', labelsize = 6)
        ax[i].xaxis.set_minor_locator(plt.MultipleLocator(10.))
        if lineids is not None :
            gd = np.where( (lines['wave'] > 15000+i*200) & ( lines['wave'] < 15200+i*200) ) [0]
            for line in lines[gd] :
                ax[i].text(line['wave'],lineids,line['label'],rotation=90,size=8,ha='center',va='bottom')
        if refline is not None :
            # plot a reference horizontal line
            plots.plotl(ax[i],wave,spec*0.+refline,xr=[15000+i*200,15200+i*200],color=color,linewidth=0.3,alpha=alpha,yr=yr,ls=':')

        if multipage :
            mfig,multiax = plots.multi(1,1)
            plots.plotl(multiax,wave,spec,xr=[15000+i*200,15200+i*200],color=color,linewidth=0.3,alpha=alpha,yr=yr)
            multiax.xaxis.label.set_size(6)
            multiax.yaxis.label.set_size(6)
            multiax.tick_params(axis = 'both', which = 'major', labelsize = 6)
            multiax.xaxis.set_minor_locator(plt.MultipleLocator(10.))
            if lineids is not None :
                gd = np.where( (lines['wave'] > 15000+i*200) & ( lines['wave'] < 15200+i*200) ) [0]
                for line in lines[gd] :
                    multiax.text(line['wave'],1.,line['label'],rotation=90,size=4,ha='left',va='bottom')

    # final panel with full wavelength range if requested
    if sum :
        plots.plotl(ax[10],wave,spec,xr=[15100,17000],color=color,linewidth=0.3,alpha=alpha,yr=yr)
        ax[10].xaxis.label.set_size(6)
        ax[10].yaxis.label.set_size(6)
        ax[10].tick_params(axis = 'both', which = 'major', labelsize = 6)
        ax[10].xaxis.set_minor_locator(plt.MultipleLocator(100.))

    try: 
        if title is not None : fig.suptitle(title)
    except: pass
    if hard is not None : fig.savefig(hard)

    try: return fig,ax
    except: return

def plotparams(a,title=None,hard=None) :
    """ Plot parameters vs Teff
    """
    fig,ax=plots.multi(1,8,hspace=0.001)

    paramnames,tagnames,flagnames = params()

    for i in range(8) :
        plots.plotc(ax[i],a['FPARAM'][:,0],a['FPARAM'][:,i],a['FPARAM'][:,3],yt=tagnames[i],xt='Teff')
    if title is not None : fig.suptitle(title)
    if hard is not None : fig.savefig(hard)

def multiwind(data,apred='r10',aspcap='t33w',out='plots/') :
    """ Plot results from different windows for each element
    """
    #load=apload.ApLoad(apred=apred,aspcap=aspcap)
    #data=load.allCal()
    els=data[3].data['ELEM_SYMBOL'][0]
    elemtoh=data[3].data['ELEMTOH'][0]
    grid=[]
    ytit=[]
    for iel,el in enumerate(els) :
        if os.path.exists(os.environ['APOGEE_ASPCAP']+'/'+apred+'/'+aspcap+'/config/apogee-n/'+el+'.wind') :
            w=np.loadtxt(os.environ['APOGEE_ASPCAP']+'/'+apred+'/'+aspcap+'/config/apogee-n/'+el+'.wind') 
            nwind=w.shape[0]
            fig,ax=plots.multi(1,nwind,hspace=0.001,figsize=(6,nwind))
            fig.suptitle(el)
            for i in range(1,nwind+1) : 
                plots.plotc(ax[i-1],data[1].data['FPARAM'][:,0],data[1].data['FELEM'][:,i,iel]-data[1].data['FELEM'][:,0,iel],
                            data[1].data['FPARAM'][:,3],xr=[3000,6000],yr=[-1,1],zr=[-2,0.5],xt='Teff',size=5,yt=r'$\Delta$(line-global)')
                ax[i-1].text(0.05,0.8,'{:8.2f}-{:8.2f}   {:8.2f}'.format(w[i-1,0],w[i-1,1],w[i-1,2]),transform=ax[i-1].transAxes,fontsize=10)
                ax[i-1].yaxis.label.set_size(6)
            fig.savefig(out+el+'.png')
            fig,ax=plots.multi(1,nwind,hspace=0.001,figsize=(6,nwind))
            fig.suptitle(el)
            for i in range(1,nwind+1) : 
                if elemtoh[iel] == 1: y = data[1].data['FELEM'][:,i,iel]-data[1].data['FPARAM'][:,3]
                else : y = data[1].data['FELEM'][:,i,iel]
                plots.plotc(ax[i-1],data[1].data['FPARAM'][:,3],y,
                            data[1].data['FPARAM'][:,0],xr=[-2.5,1.],yr=[-0.5,0.5],zr=[3500,5500],xt='[M/H]',size=5,yt='[X/M]')
                ax[i-1].text(0.05,0.8,'{:8.2f}-{:8.2f}   {:8.2f}'.format(w[i-1,0],w[i-1,1],w[i-1,2]),transform=ax[i-1].transAxes,fontsize=10)
                ax[i-1].yaxis.label.set_size(6)
            fig.savefig(out+el+'_2.png')
            grid.append([el+'.png',el+'_2.png'])
            ytit.append(el)
            plt.close()
            plt.close()
    html.htmltab(grid,ytitle=ytit,file=out+'wind.html')

def compspec(a,b,j=0,hard=None) :
    """ compare spectra and best fits from two different input aspcapField files for specified object
    """
    nplot=11
    hf,ha=plots.multi(1,nplot,figsize=(33,44),hspace=0.2)
    ha2=[]
    for i in range(nplot) : ha2.append(ha[i].twinx())
    print(hf.get_size_inches())
    chi2_a = (a[2].data['SPEC'][j,:]-a[2].data['SPEC_BESTFIT'][j,:])**2/a[2].data['ERR'][j,:]**2
    chi2_b = (b[2].data['SPEC'][j,:]-b[2].data['SPEC_BESTFIT'][j,:])**2/b[2].data['ERR'][j,:]**2
    plot(10.**a[3].data['WAVE'][0],a[2].data['SPEC'][j,:] ,sum=True,color='k',figax=(hf,ha),yr=[0.8,1.3],lineids=1.1)
    plot(10.**a[3].data['WAVE'][0],a[2].data['SPEC_BESTFIT'][j,:] ,sum=True,color='r',figax=(hf,ha),yr=[0.8,1.3])
    plot(10.**b[3].data['WAVE'][0],b[2].data['SPEC_BESTFIT'][j,:] ,sum=True,color='b',figax=(hf,ha),yr=[0.8,1.3])
    plot(10.**a[3].data['WAVE'][0],a[2].data['SPEC'][j,:]-b[2].data['SPEC_BESTFIT'][j,:]+0.95 ,sum=True,color='c',
         figax=(hf,ha),yr=[0.8,1.3],refline=0.9)
    plot(10.**a[3].data['WAVE'][0],a[2].data['SPEC_BESTFIT'][j,:]-b[2].data['SPEC_BESTFIT'][j,:]+0.9 ,sum=True,color='m',
         figax=(hf,ha),yr=[0.8,1.3],refline=0.9)
    plot(10.**a[3].data['WAVE'][0],chi2_a-chi2_b ,sum=True,color='g',multipage=False,figax=(hf,ha2),yr=[-10,10],refline=0.)
    if hard is not None : hf.savefig(hard+'.pdf')

    fig,ax=plots.multi(1,2,hspace=0.001)
    plots.plotl(ax[0],10.**a[3].data['WAVE'][0],np.cumsum(chi2_a),xt='Wavelength',yt='Cumulative chi^2')
    plots.plotl(ax[0],10.**a[3].data['WAVE'][0],np.cumsum(chi2_b))
    plots.plotl(ax[1],10.**a[3].data['WAVE'][0],np.cumsum(chi2_a)-np.cumsum(chi2_b),yt='Difference in cumulative chi^2')
    if hard is not None : fig.savefig(hard+'_chi2.pdf')
    plt.close()
    plt.close()

def vesta() :
    """ series of plots for Vesta for DR16 tests
    """
    l33_fit = fits.open(os.environ['APOGEE_ASPCAP']+'/r10/test/apo1m/fit/aspcapField-standards.fits')
    l33_fixed = fits.open(os.environ['APOGEE_ASPCAP']+'/r10/test/apo1m/fixed/aspcapField-standards.fits')
    l31c_fit = fits.open(os.environ['APOGEE_ASPCAP']+'/r10/testl31c/apo1m/fit/aspcapField-standards.fits')
    l31c_fixed = fits.open(os.environ['APOGEE_ASPCAP']+'/r10/testl31c/apo1m/fixed/aspcapField-standards.fits')
    l31crenorm_fit = fits.open(os.environ['APOGEE_ASPCAP']+'/r10/testl31crenorm/apo1m/fit/aspcapField-standards.fits')
    l31crenorm_fixed = fits.open(os.environ['APOGEE_ASPCAP']+'/r10/testl31crenorm/apo1m/fixed/aspcapField-standards.fits')
    compspec(l33_fit,l33_fixed,hard='Vesta_l33_fitvsfixed')
    compspec(l31c_fit,l31c_fixed,hard='Vesta_l31c_fitvsfixed')
    #compspec(l31c_fixed,l33_fixed,hard='Vesta_fixed_l31cvl33')
    compspec(l31crenorm_fit,l31crenorm_fixed,hard='Vesta_l31crenorm_fitvsfixed')

def repeat(data,out=None) :
    """ Comparison of repeat observations of objects
    """

    a=data[1].data
    els=data[3].data['ELEM_SYMBOL'][0]
    stars = set(a['APOGEE_ID'])
    fig,ax=plots.multi(2,7,figsize=(8,18),wspace=0.4)
    efig,eax=plots.multi(2,len(els),hspace=0.001,figsize=(8,36),wspace=0.4)
    telescope=np.zeros(len(a),dtype='S6')
    colors=['r','g','b']
    tels=['apo1m','apo25m','lco25m'] 
    for tel in tels :
        j=np.where(np.core.defchararray.find(a['ALTFIELD'],tel) >= 0)[0]
        telescope[j] = tel
    diff=[]
    ediff=[]
    tdiff=[]
    teldiff=[]
    for star in stars :
        j = np.where(a['APOGEE_ID'] == star)[0]
        n = len(j)
        if n > 1 :
            print(star,n,telescope[j])
            for i in j : 
                ediff.append(a['FELEM'][i,0,:]-a['FELEM'][j,0,:].mean(axis=0))
                diff.append(a['FPARAM'][i,:]-a['FPARAM'][j,:].mean(axis=0))
                tdiff.append(a['FPARAM'][j,0].mean())
                teldiff.append(telescope[i])
            for i in range(7)  :
                plots.plotp(ax[i,0],np.repeat(a['FPARAM'][j,0].mean(),n),a['FPARAM'][j,i]-a['FPARAM'][j,i].mean(),typeref=telescope[j],
                            types=tels,color=colors)
                #for itel,tel in enumerate(tels) :
                #    gd=np.where(np.core.defchararray.find(a['ALTFIELD'][j],tel) >= 0)[0]
                #    gd=j[gd]
            for i in range(len(els))  :
                plots.plotp(eax[i,0],np.repeat(a['FPARAM'][j,0].mean(),n),a['FELEM'][j,0,i]-a['FELEM'][j,0,i].mean(),typeref=telescope[j],
                            types=tels,color=colors,yr=[-0.2,0.2])
                #for itel,tel in enumerate(tels) :
                #    gd=np.where(np.core.defchararray.find(a['ALTFIELD'][j],tel) >= 0)[0]
                #    gd=j[gd]
                #    ax[i,1].hist(a['FELEM'][gd,i]-a['FELEM'][gd,i].mean(),color=colors[itel])
    diff=np.array(diff) 
    ediff=np.array(ediff) 
    tdiff=np.array(tdiff) 
    teldiff=np.array(teldiff) 
    for itel,tel in enumerate(tels) :
        gd=np.where(teldiff == tel)[0]
        if len(gd) > 0 :
            for i in range(7)  :
                if i == 0 : bins=np.arange(-200,200,10)
                elif i ==1 : bins=np.arange(-0.5,0.5,0.025)
                else : bins=np.arange(-0.2,0.2,0.01)
                ax[i,1].hist(diff[gd,i],color=colors[itel],histtype='step',bins=bins)
            for i in range(len(els))  :
                bins=np.arange(-0.2,0.2,0.01)
                try: eax[i,1].hist(ediff[gd,i],color=colors[itel],histtype='step',bins=bins)
                except: pass
    for i,el in enumerate(els) : 
        eax[i,0].set_ylabel(el)
        eax[i,1].text(0.1,0.9,el,transform=eax[i,1].transAxes)
    for i,param in enumerate(data[3].data['PARAM_SYMBOL'][0]) : 
        if i < 7 :
            ax[i,0].set_ylabel(param)
            ax[i,1].text(0.1,0.9,param,transform=ax[i,1].transAxes)
    if out is not None :
        fig.savefig(out+'param_diff.png')
        efig.savefig(out+'elem_diff.png')
    else :
        pdb.set_trace()
    plt.close(fig)
    plt.close(efig)
