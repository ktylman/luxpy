# -*- coding: utf-8 -*-
"""
Model new daylihgt locus for specific CMF set.


References:
    Judd, D. B., MacAdam, D. L., Wyszecki, G., Budde, H. W., Condit, H. R., Henderson, S. T., & Simonds, J. L. (1964). Spectral Distribution of Typical Daylight as a Function of Correlated Color Temperature. J. Opt. Soc. Am., 54(8), 1031–1040. https://doi.org/10.1364/JOSA.54.001031

Created on Wed Jul  8 19:04:04 2020

@author: u0032318
"""

from luxpy import daylightphase, spd_to_xyz, _CMF
from luxpy.utils import np, sp, plt, np2d

def _get_daylightlocus_parameters(ccts, spds, cieobs):
    """
    Get daylight locus parameters for a single cieobs from daylight phase spectra
    determined based on parameters for '1931_2' as reported in CIE15-20xx.
    """
    # get xy coordinates for new cieobs:
    xyz = spd_to_xyz(spds, cieobs = cieobs)
    xy = xyz[...,:2]/xyz.sum(axis=-1,keepdims=True)
    
    # Fit 3e order polynomal xD(1/T) [4000 K < T <= 7000 K]:
    l7 = ccts<=7000
    pxT_l7 = np.polyfit((1000/ccts[l7]), xy[l7,0],3)  
    
    # Fit 3e order polynomal xD(1/T) [T > 7000 K]:
    L7 = ccts>7000
    pxT_L7 = np.polyfit((1000/ccts[L7]), xy[L7,0],3)  
    
    # Fit 2nd order polynomal yD(xD):
    pxy = np.round(np.polyfit(xy[:,0],xy[:,1],2),3)
    #pxy = np.hstack((0,pxy)) # make also 3e order for easy stacking
    
    return xy, pxy, pxT_l7, pxT_L7, l7, L7

def get_daylightloci_parameters(ccts = None, cieobs = None, wl3 = [300,830,10], verbosity = 0):
    """
    Get parameters for the daylight loci functions xD(1000/CCT) and yD(xD).
    
    Args:
        :ccts:
            | None, optional
            | ndarray with CCTs, if None: ccts = np.arange(4000,25000,250)
        :cieobs:
            | None or list, optional
            | CMF sets to determine parameters for.
            | If None: get for all CMFs sets in _CMF (except scoptopic and deviate observer)
        :wl3:
            | [300,830,10], optional
            | Wavelength range and spacing of daylight phases to be determined
            | from '1931_2'. The default setting results in parameters very close
            | to that in CIE15-2004/2018.
        :verbosity:
            | 0, optional
            | print parameters and make plots.
            
    Returns:
        :dayloci:
            | dict with parameters for each cieobs
    """
    if ccts is None:
        ccts = np.arange(4000,25000,250)
        
    # Get daylight phase spds using cieobs '1931_2':
    # wl3 = [300,830,10] # results in Judd's (1964) coefficients for the function yD(xD)x; other show slight deviations
    for i, cct  in enumerate(ccts):
        spd = daylightphase(cct, wl3 = wl3, force_daylight_below4000K = False)
        if i == 0:
            spds = spd
        else:
            spds = np.vstack((spds,spd[1:]))
            
    if verbosity > 0:
        fig,axs = plt.subplots(nrows = 2, ncols = len(_CMF['types']) - 2)   # -2: don't include scoptopic and dev observers     
    
    dayloci = {}
    i = 0
    for cieobs in _CMF['types']:
        if 'scotopic' in cieobs:
            continue
        if 'std_dev_obs' in cieobs:
            continue
        
        # get parameters for cieobs:
        xy, pxy, pxT_l7, pxT_L7, l7, L7 = _get_daylightlocus_parameters(ccts, spds, cieobs)
        dayloci[cieobs] = {'pxT_l7k':pxT_l7, 'pxT_L7k':pxT_L7, 'pxy':pxy}
        
        if verbosity > 0:
            print('\n cieobs:', cieobs)
            print('pxT_l7 (4000 K < T <= 7000 K):',pxT_l7)
            print('pxT_L7 (T > 7000 K):',pxT_L7)
            print('p:xy',pxy)
                  
            axs[0,i].plot(ccts, xy[:,0],'r-')
            axs[0,i].plot(ccts[l7], np.polyval(pxT_l7,1000/ccts[l7]),'b--')
            axs[0,i].plot(ccts[L7], np.polyval(pxT_L7,1000/ccts[L7]),'c--')
            axs[0,i].set_title(cieobs)
            axs[0,i].set_xlabel('CCT (K)')
            axs[0,i].set_ylabel('xD')
            
            plotSL(cieobs = cieobs, cspace = 'Yxy', DL = False, axh = axs[1,i])
            axs[1,i].plot(xy[:,0],xy[:,1],'r-')
            axs[1,i].plot(xy[:,0],np.polyval(pxy,xy[:,0]),'b--')
            # axs[1,i].plot(xy[:,0],np.polyval(pxy_31,xy[:,0]),'g:')
        
        i+=1
        
    return dayloci

_DAYLIGHT_LOCI_PARAMETERS = get_daylightloci_parameters(ccts = None, cieobs = None, wl3 = [300,830,10], verbosity = 0)


def daylightlocus(cct, force_daylight_below4000K = False, cieobs = None, daylight_locus = None):
    """ 
    Calculates daylight chromaticity (xD,yD) from correlated color temperature (cct).
    
    Args:
        :cct: 
            | int or float or list of int/floats or ndarray
        :force_daylight_below4000K: 
            | False or True, optional
            | Daylight locus approximation is not defined below 4000 K, 
            | but by setting this to True, the calculation can be forced to 
            | calculate it anyway.
        :cieobs:
            | CMF set corresponding to xD, yD output.
            | If None: use default CIE15-20xx locus for '1931_2'
            | Else: use the locus specified in :daylight_locus:
        :daylight_locus:
            | None, optional
            | dict with xD(T) and yD(xD) parameters to calculate daylight locus 
            | for specified cieobs.
            | If None: use pre-calculated values.
            | If 'calc': calculate them on the fly.
    
    Returns:
        :(xD, yD): 
            | (ndarray of x-coordinates, ndarray of y-coordinates)
        
    References:
        1. `CIE15:2018, “Colorimetry,” CIE, Vienna, Austria, 2018. <https://doi.org/10.25039/TR.015.2018>`_
    """
    cct = np2d(cct)
    if np.any((cct < 4000.0) & (force_daylight_below4000K == False)):
        raise Exception('spectral.daylightlocus(): Daylight locus approximation not defined below 4000 K')
    
    if (cieobs is None): # use default values for '1931_2' reported in CIE15-20xx
        xD = -4.607*((1e3/cct)**3.0)+2.9678*((1e3/cct)**2.0)+0.09911*(1000.0/cct)+0.244063
        p = cct>=7000.0
        xD[p] = -2.0064*((1.0e3/cct[p])**3.0)+1.9018*((1.0e3/cct[p])**2.0)+0.24748*(1.0e3/cct[p])+0.23704
        yD = -3.0*xD**2.0+2.87*xD-0.275
    else:
        if daylight_locus is None:
            daylight_locus = _DAYLIGHT_LOCI_PARAMETERS[cieobs]
        elif daylight_locus is 'calc':
            daylight_locus = get_daylightloci_parameters(cieobs = [cieobs])['cieobs']
        pxy, pxT_l7, pxT_L7 = daylight_locus['pxy'], daylight_locus['pxT_l7k'], daylight_locus['pxT_L7k']
        xD = np.polyval(pxT_l7, 1000/cct)
        p = cct>=7000.0
        xD[p] = np.polyval(pxT_l7, 1000/cct[p])
        yD = np.polyval(pxy, xD)        
        
    return xD,yD

if __name__ == '__main__':
    dayloci = get_daylightloci_parameters(ccts = None, cieobs = None, wl3 = [300,830,10], verbosity = 1)

    # test code:
    xD,yD = daylightlocus(4500,cieobs=None, daylight_locus = None)
    xD_,yD_ = daylightlocus(4500,cieobs='1931_2', daylight_locus = None)
    
    