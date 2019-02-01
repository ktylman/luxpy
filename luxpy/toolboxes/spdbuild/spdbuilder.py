# -*- coding: utf-8 -*-
"""
Module for building and optimizing SPDs
=======================================

Functions
---------

 :gaussian_spd(): Generate Gaussian spectrum.

 :butterworth_spd(): Generate Butterworth based spectrum.

 :mono_led_spd(): Generate monochromatic LED spectrum based on a Gaussian 
                  or butterworth profile or according to Ohno (Opt. Eng. 2005).

 :spd_builder(): Build spectrum based on Gaussians, monochromatic 
                 and/or phophor LED spectra.

 :color3mixer(): Calculate fluxes required to obtain a target chromaticity 
                 when (additively) mixing 3 light sources.

 :colormixer(): Calculate fluxes required to obtain a target chromaticity 
                when (additively) mixing N light sources.

 :spd_builder(): Build spectrum based on Gaussians, monochromatic 
                 and/or phophor LED-type spectra.
                   
 :get_w_summed_spd(): Calculate weighted sum of spds.
 
 :fitnessfcn(): Fitness function that calculates closeness of solution x to 
                target values for specified objective functions.
         
 :spd_constructor_2(): Construct spd from spectral model parameters 
                       using pairs of intermediate sources.
                
 :spd_constructor_3(): Construct spd from spectral model parameters 
                       using trio's of intermediate sources.
     
 :spd_optimizer_2_3(): Optimizes the weights (fluxes) of a set of component 
                       spectra by combining pairs (2) or trio's (3) of 
                       components to intermediate sources until only 3 remain.
                       Color3mixer can then be called to calculate required 
                       fluxes to obtain target chromaticity and fluxes are 
                       then back-calculated.                                   
                        
 :get_optim_pars_dict(): Setup dict with optimization parameters.
                        
 :initialize_spd_model_pars(): Initialize spd_model_pars (for spd_constructor)
                               based on type of component_data.

 :initialize_spd_optim_pars(): Initialize spd_optim_pars (x0, lb, ub for use
                               with math.minimizebnd) based on type 
                               of component_data.
                
 :spd_optimizer(): Generate a spectrum with specified white point and optimized
                   for certain objective functions from a set of component 
                   spectra or component spectrum model parameters.
                
References
----------
    1. `Ohno Y (2005). 
    Spectral design considerations for white LED color rendering. 
    Opt. Eng. 44, 111302. 
    <https://ws680.nist.gov/publication/get_pdf.cfm?pub_id=841839>`_

.. codeauthor:: Kevin A.G. Smet (ksmet1977 at gmail.com)
"""
from luxpy import (np, plt, warnings, math, _WL3, _CIEOBS, _EPS, np2d, 
                   vec_to_dict, getwlr, SPD,
                   spd_to_xyz, xyz_to_Yxy, colortf, xyz_to_cct)
from luxpy import cri 
import itertools

#np.set_printoptions(formatter={'float': lambda x: "{0:0.2e}".format(x)})

__all__ = ['gaussian_spd','mono_led_spd','phosphor_led_spd','spd_builder',
         'get_w_summed_spd','fitnessfcn','spd_constructor_2',
         'spd_constructor_3','spd_optimizer_2_3','get_optim_pars_dict',
         'initialize_spd_model_pars','initialize_spd_optim_pars','spd_optimizer']

#------------------------------------------------------------------------------
def gaussian_spd(peakwl = 530, fwhm = 20, wl = _WL3, with_wl = True):
    """
    Generate Gaussian spectrum.
    
    Args:
        :peakw: 
            | int or float or list or ndarray, optional
            | Peak wavelength
        :fwhm:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian.
        :wl: 
            | _WL3, optional 
            | Wavelength range.
        :with_wl:
            | True, optional
            | True outputs a ndarray with first row wavelengths.
    
    Returns:
        :returns:
            | ndarray with spectra.        
    """
    wl = np.atleast_2d(getwlr(wl)).T # create wavelength range
    spd = np.exp(-0.5*((wl-np.atleast_2d(peakwl))/np.atleast_2d(fwhm))**2)
    if with_wl == True:
        spd = np.vstack((wl, spd))
    return spd.T


#------------------------------------------------------------------------------
def butterworth_spd(peakwl = 530, fwhm = 20, bw_order = 1, wl = _WL3, with_wl = True):
    """
    Generate Butterworth based spectrum.
    
    Args:
        :peakw: 
            | int or float or list or ndarray, optional
            | Peak wavelength
        :fwhm:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian.
        :bw_order: 
            | 1, optional
            | Order of the butterworth function.
        :wl:
            | _WL3, optional 
            | Wavelength range.
        :with_wl:
            | True, optional
            | True outputs a ndarray with first row wavelengths.
    
    Returns:
        :returns:
            | ndarray with spectra.        
    """
    wl = np.atleast_2d(getwlr(wl)).T # create wavelength range
    spd = 2 / (1 + np.abs((wl-np.atleast_2d(peakwl))/np.atleast_2d(fwhm))**(2*np.atleast_2d(bw_order)))
    if with_wl == True:
        spd = np.vstack((wl, spd))
    return spd.T

#------------------------------------------------------------------------------
def mono_led_spd(peakwl = 530, fwhm = 20, wl = _WL3, with_wl = True, strength_shoulder = 2, bw_order = -1):
    """
    Generate monochromatic LED spectrum based on a Gaussian or butterworth
    profile or according to Ohno (Opt. Eng. 2005).
        
    Args:
        :peakw:
            | int or float or list or ndarray, optional
            | Peak wavelength
        :fwhm:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian used to simulate led.
        :wl: 
            | _WL3, optional 
            |  Wavelength range.
        :with_wl:
            | True, optional
            | True outputs a ndarray with first row wavelengths.
        :strength_shoulder:
            | 2, optional
            | Determines the strength of the spectrum shoulders of the mono led.
            | A value of 1 reduces to a Gaussian model (if bw_order == 0).
        :bw_order:
            | -1, optional
            | Order of Butterworth function.
            | If -1: spd profile is Gaussian.
            | If (bw_order == 0): spd profile is Gaussian, else Butterworth.
    
    Returns:
        :returns:
            | ndarray with spectra.   
    
    Note:
        | Gaussian:
        |    g = exp(-0.5*((wl - peakwl)/fwhm)**2)
        | 
        | Butterworth :
        |    bw = 2 / (1 + (((wl - peakwl)/fwhm)**2))
        | 
        | Ohno's model:
        |    ohno = (g + strength_shoulder*g**5)/(1+strength_shoulder)
        |     
        |    mono_led_spd = ohno*(bw_order == 0) + bw*(bw_order > 0)
    
    Reference:
        1. `Ohno Y (2005). 
        Spectral design considerations for white LED color rendering. 
        Opt. Eng. 44, 111302. 
        <https://ws680.nist.gov/publication/get_pdf.cfm?pub_id=841839>`_

    """
    g = gaussian_spd(peakwl = peakwl, fwhm = fwhm, wl = wl, with_wl = False)
    ohno = (g + np.atleast_2d(strength_shoulder)*g**5)/(1+np.atleast_2d(strength_shoulder))
    bw_order = np.atleast_2d(bw_order)
    if (bw_order == -1).all():
        spd = ohno
    else:
        bw = butterworth_spd(peakwl = peakwl, fwhm = fwhm, wl = wl, bw_order = bw_order, with_wl = False)
        spd = ohno*(bw_order == 0).T + bw*(bw_order > 0).T
    if with_wl == True:
        spd = np.vstack((getwlr(wl), spd))
    return spd

#------------------------------------------------------------------------------
def phosphor_led_spd(peakwl = 450, fwhm = 20, wl = _WL3, bw_order = -1, with_wl = True, strength_shoulder = 2,\
                    strength_ph = 0, peakwl_ph1 = 530, fwhm_ph1 = 80, strength_ph1 = 1,\
                    peakwl_ph2 = 560, fwhm_ph2 = 80, strength_ph2 = None,\
                    use_piecewise_fcn = False,\
                    verbosity = 0, out = 'spd'):
    """
    Generate phosphor LED spectrum with up to 2 phosphors based on Smet (Opt. Expr. 2011).
    
    | Model:
    |    1) If strength_ph2 is not None:
    |          phosphor_spd = (strength_ph1*mono_led_spd(peakwl_ph1, ..., strength_shoulder = 1) 
    |                       + strength_ph2)*mono_led_spd(peakwl_ph2, ..., strength_shoulder = 1)) 
    |                        / (strength_ph1 + strength_ph2)
    |      else:
    |          phosphor_spd = (strength_ph1*mono_led_spd(peakwl_ph1, ..., strength_shoulder = 1) 
    |                       + (1-strength_ph1)*mono_led_spd(peakwl_ph2, ..., strength_shoulder = 1)) 
    |
    |    2) S = (mono_led_spd() + strength_ph*(phosphor_spd/phosphor_spd.max()))/(1 + strength_ph)
    |    
    |    3) piecewise_fcn = S for wl < peakwl and 1 for wl >= peakwl
    |    
    |    4) phosphor_led_spd = S*piecewise_fcn 
            
    Args:
        :peakw:
            | int or float or list or ndarray, optional
            | Peak wavelengths of the monochromatic led.
        :fwhm:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian.
        :wl: | _WL3, optional 
            | Wavelength range.
        :bw_order:
            | -1, optional
            | Order of Butterworth function.
            | If -1: mono_led spd profile is Gaussian.
            | else: (bw_order == 0): spd profile is Gaussian, else Butterworth.
            | Note that this only applies to the monochromatic led  spds and not 
            | the phosphors spds (these are always gaussian based).
        :with_wl:
            | True, optional
            | True outputs a ndarray with first row wavelengths.
        :strength_shoulder: 
            | 2, optiona l
            | Determines the strength of the spectrum shoulders of the mono led.
        :strength_ph:
            | 0, optional
            | Total contribution of phosphors in mixture.
        :peakwl_ph1:
            | int or float or list or ndarray, optional
            | Peak wavelength of the first phosphor.
        :fwhm_ph1:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian used to simulate first phosphor.
        :strength_ph1:
            | 1, optional
            | Strength of first phosphor in phosphor mixture. 
            | If :strength_ph2: is None: value should be in the [0,1] range.
        :peakwl_ph2:
            | int or float or list or ndarray, optional
            | Peak wavelength of the second phosphor.
        :fwhm_ph2: 
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian used to simulate second phosphor.
        :strength_ph2:
            | None, optional
            | Strength of second phosphor in phosphor mixture. 
            | If None: strength is calculated as (1-:strength_ph1:)
            |     :target: np2d([100,1/3,1/3]), optional
            |  ndarray with Yxy chromaticity of target.
        :verbosity:
            | 0, optional
            | If > 0: plots spectrum components (mono_led, ph1, ph2, ...)
        :out: 
            | 'spd', optional
            | Specifies output.
        :use_piecewise_fcn:
            | False, optional
            | True: uses piece-wise function as in Smet et al. 2011. Can give 
              non_smooth spectra optimized from components to which it is
              applied. 
            
    Returns:
        :returns: 
            | spd, component_spds
            | ndarrays with spectra (and component spds used to build the 
              final spectra) 
        
        
    References:
        1. `Ohno Y (2005). 
        Spectral design considerations for white LED color rendering. 
        Opt. Eng. 44, 111302. 
        <https://ws680.nist.gov/publication/get_pdf.cfm?pub_id=841839>`_

        2. `Smet K, Ryckaert WR, Pointer MR, Deconinck G, and Hanselaer P (2011). 
        Optimal colour quality of LED clusters based on memory colours. 
        Opt. Express 19, 6903–6912.
        <https://www.osapublishing.org/vjbo/fulltext.cfm?uri=oe-19-7-6903&id=211315>`_
    """
        
    mono_led = mono_led_spd(peakwl = peakwl, fwhm = fwhm, wl = wl, bw_order = bw_order, with_wl = False, strength_shoulder = strength_shoulder)
    wl = getwlr(wl)
    if strength_ph is not None:
        strength_ph = np.atleast_2d(strength_ph)
        if ((strength_ph > 0).any()): # Use phophor type led for obtaining target:
            ph1 = mono_led_spd(peakwl = peakwl_ph1, fwhm = fwhm_ph1, wl = wl, with_wl = False, strength_shoulder = 1)
            ph2 = mono_led_spd(peakwl = peakwl_ph2, fwhm = fwhm_ph2, wl = wl, with_wl = False, strength_shoulder = 1)
            component_spds = np.dstack((mono_led,ph1,ph2))
           
            if ('spd' in out.split(',')):
                strength_ph1 = np.atleast_2d(strength_ph1)
                strength_ph2 = np.atleast_2d(strength_ph2)
                if ((ph1 is not None) & (ph2 is not None)):
                    if (strength_ph2[0,0] is not None):
                        phosphors = (strength_ph1*ph1.T + strength_ph2*ph2.T).T/(strength_ph1 + strength_ph2 + _EPS).T + _EPS
                    else:
                        phosphors = (strength_ph1*ph1.T + (1-strength_ph1)*ph2.T).T + _EPS
                    strength_ph = np.atleast_1d(strength_ph)
                    phosphors = phosphors/phosphors.max(axis = 1, keepdims = True)
                    
                    spd = mono_led + (strength_ph*phosphors.T).T
                else:
                    phosphors = None
                    spd = mono_led.copy()
                
        else: # Only monochromatic leds:
            ph1 = None
            ph2 = None
            phosphors = None
            spd = mono_led.copy()
            component_spds = mono_led[:,:,None].T.copy()
    
    else: # Only monochromatic leds:
        ph1 = None
        ph2 = None
        phosphors = None
        spd = mono_led.copy()
        component_spds = mono_led[:,:,None].T.copy()


    if (use_piecewise_fcn == True):
        peakwl = np.atleast_1d(peakwl)
        if ('component_spds' in out.split(',')):
            fp = component_spds.copy()
            for i in range(fp.shape[0]):
                fp[i,np.where(wl >= peakwl[i]),:] = 1
                component_spds[...,i] = component_spds[...,i]*fp[...,i] # multiplication with piecewise function f'
        if ('spd' in out.split(',')):
            fp = mono_led.copy()
            for i in range(fp.shape[0]):
                fp[i,np.where(wl >= peakwl[i])] = 1
                spd[i] = spd[i]*fp[i] # multiplication with piecewise function f'

    # Normalize to max = 1:
    spd = spd/spd.max(axis = 1, keepdims = True)
    component_spds = component_spds/component_spds.max(axis=1,keepdims=True)

    if verbosity > 0:
        mono_led_str = 'Mono_led_1'
        ph1_str = 'Phosphor_1'
        ph2_str = 'Phosphor_2'
        for i in range(spd.shape[0]):
            plt.figure()
            if ph1 is not None:
                plt.plot(wl,mono_led[i].T,'b--', label = mono_led_str)
                plt.plot(wl,ph1[i].T,'g:', label = ph1_str)
                plt.plot(wl,ph2[i].T,'y:', label = ph2_str)
                if phosphors is not None:
                    plt.plot(wl,phosphors[i].T,'r--', label = 'Ph1,2 combined')
            plt.plot(wl,spd[i].T,'k-', label = 'Output spd')
            plt.xlabel('Wavelengths (nm)')
            plt.ylabel('Normalized spectral intensity (max = 1)')
            plt.legend()
            plt.show()

    if (with_wl == True):
        spd = np.vstack((wl, spd))
        component_spds = np.vstack((wl, component_spds))

    if out == 'spd':
        return spd
    elif out == 'component_spds':
        return component_spds
    elif out == 'spd,component_spds':
        return spd, component_spds


#------------------------------------------------------------------------------
def spd_builder(flux = None, component_spds = None, peakwl = 450, fwhm = 20, bw_order = -1,\
                pair_strengths = None, wl = _WL3, with_wl = True, strength_shoulder = 2,\
                strength_ph = 0, peakwl_ph1 = 530, fwhm_ph1 = 80, strength_ph1 = 1,\
                peakwl_ph2 = 560, fwhm_ph2 = 80, strength_ph2 = None,\
                target = None, tar_type = 'Yuv', cspace_bwtf = {}, cieobs = _CIEOBS,\
                use_piecewise_fcn = False, verbosity = 0, out = 'spd',**kwargs):
    """
    Build spectrum based on Gaussian, monochromatic and/or phophor type spectra.
           
    Args:
        :flux: 
            | None, optional
            | Fluxes of each of the component spectra.
            | None outputs the individual component spectra.
        :component_spds:
            | None or ndarray, optional
            | If None: calculate component spds from input args.
        :peakw:
            | int or float or list or ndarray, optional
            | Peak wavelengths of the monochromatic led.
        :fwhm:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian.
        :wl:
            | _WL3, optional
            | Wavelength range.
        :bw_order:
            | -1, optional
            | Order of Butterworth function.
            | If -1: mono_led spd profile is Gaussian.
            | else: (bw_order == 0): spd profile is Gaussian, else Butterworth.
            | Note that this only applies to the monochromatic led  spds and not 
            | the phosphors spds (these are always gaussian based).
        :pair_strengths:
            | ndarray with pair_strengths of mono_led spds, optional
            | If None: will be randomly selected, possibly resulting in 
              unphysical (out-of-gamut) solution.
        :with_wl:
            | True, optional
            | True outputs a ndarray with first row wavelengths.
        :strength_shoulder: 
            | 2, optiona l
            | Determines the strength of the spectrum shoulders of the mono led.
        :strength_ph:
            | 0, optional
            | Total contribution of phosphors in mixture.
        :peakwl_ph1:
            | int or float or list or ndarray, optional
            | Peak wavelength of the first phosphor.
        :fwhm_ph1:
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian used to simulate first phosphor.
        :strength_ph1:
            | 1, optional
            | Strength of first phosphor in phosphor mixture. 
            | If :strength_ph2: is None: value should be in the [0,1] range.
        :peakwl_ph2:
            | int or float or list or ndarray, optional
            | Peak wavelength of the second phosphor.
        :fwhm_ph2: 
            | int or float or list or ndarray, optional
            | Full-Width-Half-Maximum of gaussian used to simulate second phosphor.
        :strength_ph2:
            | None, optional
            | Strength of second phosphor in phosphor mixture. 
            | If None: strength is calculated as (1-:strength_ph1:)
            |     :target: np2d([100,1/3,1/3]), optional
            |  ndarray with Yxy chromaticity of target.
        :verbosity:
            | 0, optional
            | If > 0: plots spectrum components (mono_led, ph1, ph2, ...)
        :out: 
            | 'spd', optional
            | Specifies output.
        :use_piecewise_fcn:
            | False, optional
            | True: uses piece-wise function as in Smet et al. 2011. Can give 
              non_smooth spectra optimized from components to which it is
              applied. 
        :target: 
            | None, optional
            | ndarray with Yxy chromaticity of target.
            |  If None: don't override phosphor strengths, else calculate strength
            |           to obtain :target: using color3mixer().
            | If not None AND strength_ph is None or 0: components are 
              monochromatic and colormixer is used to optimize fluxes to 
              obtain target chromaticity (N can be > 3 components)
        :tar_type:
            | 'Yxy' or str, optional
            | Specifies the input type in :target: (e.g. 'Yxy' or 'cct')
        :cieobs:
            | _CIEOBS, optional
            | CIE CMF set used to calculate chromaticity values.
        :cspace_bwtf:
            | {}, optional
            | Backward (..._to_xyz) transform parameters 
            | (see colortf()) to go from :tar_type: to 'Yxy')
            
    Returns:
        :returns: 
            | ndarray with spectra.  
    
    Note:
        1. Target-optimization is only for phophor_leds with three components 
        (blue pump, ph1 and ph2) spanning a sufficiently large gamut. 
        
    References:
        1. `Ohno Y (2005). 
        Spectral design considerations for white LED color rendering. 
        Opt. Eng. 44, 111302. 
        <https://ws680.nist.gov/publication/get_pdf.cfm?pub_id=841839>`_

        2. `Smet K, Ryckaert WR, Pointer MR, Deconinck G, and Hanselaer P (2011). 
        Optimal colour quality of LED clusters based on memory colours. 
        Opt. Express 19, 6903–6912.
        <https://www.osapublishing.org/vjbo/fulltext.cfm?uri=oe-19-7-6903&id=211315>`_
    """

    if component_spds is None:
        spd, component_spds = phosphor_led_spd(peakwl = peakwl, fwhm = fwhm, wl = wl, bw_order = bw_order, with_wl = False, strength_shoulder = strength_shoulder,\
                                           strength_ph = strength_ph, peakwl_ph1 = peakwl_ph1, fwhm_ph1 = fwhm_ph1, strength_ph1 = strength_ph1,\
                                           peakwl_ph2 = peakwl_ph2, fwhm_ph2 = fwhm_ph2, strength_ph2 = strength_ph2,\
                                           use_piecewise_fcn = use_piecewise_fcn, verbosity = 0, out = 'spd,component_spds')
        
        wl = getwlr(wl)
        
    else:
        wl = component_spds[0]
        spd = component_spds[1:]
        component_spds = component_spds[1:][:,:,None].T

    if target is not None: 
        # use component_spectra to build spds with target chromaticity
        # (ignores strength_ph values).
        N = np.int(component_spds.shape[0]) # rgb components are grouped 

        if component_spds.shape[-1] < 3:
            raise Exception('spd_builder(): Not enough component spectra for color3mixer(). Min. is 3')
        
        temp = component_spds.copy()
        temp = temp.transpose((2,0,1)).reshape((temp.shape[0]*temp.shape[-1],temp.shape[1]))
        component_spds_2d = np.vstack((wl,temp))
                
        # Calculate xyz of components:
        xyzi = spd_to_xyz(component_spds_2d, relative = False, cieobs = cieobs)

        # Calculate Yxy:
        Yxyt = colortf(target, tf = tar_type+'>Yxy', bwtf = cspace_bwtf)
        Yxyi = xyz_to_Yxy(xyzi) #input for color3mixer is Yxy
        
#        if verbosity > 0:
#            plt.figure()
#            plt.plot(Yxyt[0,1],Yxyt[0,2],'k+')
#            plt.plot(Yxyi[:N,1],Yxyi[:N,2],'bd')
#            plt.plot(Yxyi[N:2*N,1],Yxyi[N:2*N,2],'gs')
#            plt.plot(Yxyi[2*N:3*N,1],Yxyi[2*N:3*N,2],'rp')
#            plt.plot(Yxyi[3*N:4*N,1],Yxyi[3*N:4*N,2],'mo')
#            plotSL(cspace ='Yxy')

        # Calculate fluxes for obtaining target chromaticity:
        if component_spds.shape[0] == 1: # mono_led spectra can have more than 3 componenents
            if pair_strengths is None:
                M = np.asarray(np.nan)
                while (np.isnan(M).any()) & (M.size!=3): #if outside of gamut for 3 components than it will always be outside of gamut
                    M = colormixer(Yxyt = Yxyt, Yxyi = Yxyi, pair_strengths = pair_strengths)
            else:
                M = colormixer(Yxyt = Yxyt, Yxyi = Yxyi, pair_strengths = pair_strengths)
            M[np.isnan(M)] = -1

        else:
            M = color3mixer(Yxyt,Yxyi[:N,:],Yxyi[N:2*N,:],Yxyi[2*N:3*N,:]) # phosphor type spectra (3 components)

        # Calculate spectrum:
        spd = math.dot23(M,component_spds.T)
        spd = np.atleast_2d([spd[i,:,i] for i in range(N)])
        spd = spd/spd.max(axis = 1, keepdims = True)
        
        
        # Mark out_of_gamut solution with NaN's:
        is_out_of_gamut =  np.where(((M<0).sum(axis=1))>0)[0]
        spd[is_out_of_gamut,:] = np.nan
        M[is_out_of_gamut,:] = np.nan
        if verbosity > 0:
            if is_out_of_gamut.sum()>0:
                warnings.warn("spd_builder(): At least one solution is out of gamut. Check for NaN's in spd.")

    if verbosity > 0:
        if target is None:
            component_spds_plot = component_spds.T.copy()
        else:
            component_spds_plot = component_spds.copy()
        for i in range(spd.shape[0]):
            plt.figure()
            if component_spds_plot.shape[0] == 3:
                plt.plot(wl,component_spds_plot[i,:,0],'b--', label = 'Component 1')
                if (strength_ph is not None) & (strength_ph is not 0):
                    plt.plot(wl,component_spds_plot[i,:,1],'g:', label = 'Component 2')
                    plt.plot(wl,component_spds_plot[i,:,2],'y:', label = 'Component 3')
            plt.plot(wl,spd[i],'k-', label = 'Output spd')
            plt.xlabel('Wavelengths (nm)')
            plt.ylabel('Normalized spectral intensity (max = 1)')
            plt.legend()
            plt.show()

    if (flux is not None):
        flux = np.atleast_2d(flux)
        if (flux.shape[1] == spd.shape[0]):
            spd_is_not_nan = np.where(np.isnan(spd[:,0])==False)[0] #keep only not nan spds
            spd = np.dot(flux[:,spd_is_not_nan],spd[spd_is_not_nan,:])

    if not np.isnan(spd).any():
        spd = spd/spd.max(axis=1,keepdims= True)
    
    
    if with_wl == True:
        spd = np.vstack((wl, spd))
    
    if out == 'spd':
        return spd
    elif out == 'M':
        return M
    elif out == 'spd,M':
        return spd, M
    elif out == 'spd,M,component_spds':
        return spd, M, component_spds
#    elif out == 'component_spds':
#        return component_spds
    elif out == 'spd,component_spds':
        return spd, component_spds
    else:
        return eval(out)




   
#------------------------------------------------------------------------------
def color3mixer(Yxyt,Yxy1,Yxy2,Yxy3):
    """
    Calculate fluxes required to obtain a target chromaticity 
    when (additively) mixing 3 light sources.
    
    Args:
        :Yxyt: 
            | ndarray with target Yxy chromaticities.
        :Yxy1: 
            | ndarray with Yxy chromaticities of light sources 1.
        :Yxy2:
            | ndarray with Yxy chromaticities of light sources 2.
        :Yxy3:
            | ndarray with Yxy chromaticities of light sources 3.
        
    Returns:
        :M: 
            | ndarray with fluxes.
        
    Note:
        Yxyt, Yxy1, ... can contain multiple rows, referring to single mixture.
    """
    Y1 = Yxy1[...,0]
    x1 = Yxy1[...,1]
    y1 = Yxy1[...,2]
    Y2 = Yxy2[...,0]
    x2 = Yxy2[...,1]
    y2 = Yxy2[...,2]
    Y3 = Yxy3[...,0]
    x3 = Yxy3[...,1]
    y3 = Yxy3[...,2]
    Yt = Yxyt[...,0]
    xt = Yxyt[...,1]
    yt = Yxyt[...,2]
    m1 = y1*((xt-x3)*y2-(yt-y3)*x2+x3*yt-xt*y3)/(yt*((x3-x2)*y1+(x2-x1)*y3+(x1-x3)*y2))
    m2 = -y2*((xt-x3)*y1-(yt-y3)*x1+x3*yt-xt*y3)/(yt*((x3-x2)*y1+(x2-x1)*y3+(x1-x3)*y2))
    m3 = y3*((x2-x1)*yt-(y2-y1)*xt+x1*y2-x2*y1)/(yt*((x2-x1)*y3-(y2-y1)*x3+x1*y2-x2*y1))
    M = Yt*np.vstack((m1/Y1,m2/Y2,m3/Y3))
#    a = (Yxyt[...,2]*((Yxy3[...,1]-Yxy2[...,1])*Yxy1[...,2]+(Yxy2[...,1]-Yxy1[...,1])*Yxy3[...,2]+(Yxy1[...,1]-Yxy3[...,1])*Yxy2[...,2]))
#    b = (Yxyt[...,2]*((Yxy2[...,1]-Yxy1[...,1])*Yxy3[...,2]-(Yxy2[...,2]-Yxy1[...,2])*Yxy3[...,1]+Yxy1[...,1]*Yxy2[...,2]-Yxy2[...,1]*Yxy1[...,2]))
#    m1 = Yxy1[...,2]*((Yxyt[...,1]-Yxy3[...,1])*Yxy2[...,2]-(Yxyt[...,2]-Yxy3[...,2])*Yxy2[...,1]+Yxy3[...,1]*Yxyt[...,2]-Yxyt[...,1]*Yxy3[...,2])/a
#    m2 = -Yxy2[...,2]*((Yxyt[...,1]-Yxy3[...,1])*Yxy1[...,2]-(Yxyt[...,2]-Yxy3[...,2])*Yxy1[...,1]+Yxy3[...,1]*Yxyt[...,2]-Yxyt[...,1]*Yxy3[...,2])/a
#    m3 = Yxy3[...,2]*((Yxy2[...,1]-Yxy1[...,1])*Yxyt[...,2]-(Yxy2[...,2]-Yxy1[...,2])*Yxyt[...,1]+Yxy1[...,1]*Yxy2[...,2]-Yxy2[...,1]*Yxy1[...,2])/b
#    M = Yxyt[...,0]*np.vstack((m1/Yxy1[...,0],m2/Yxy2[...,0],m3/Yxy3[...,0]))
    return M.T


def colormixer(Yxyt = None, Yxyi = None, n = 4, pair_strengths = None, source_order = None):
    """
    Calculate fluxes required to obtain a target chromaticity 
    when (additively) mixing N light sources.
    
    Args:
        :Yxyt: 
            | ndarray with target Yxy chromaticities.
            | Defaults to equi-energy white.
        :Yxyi:
            | ndarray with Yxy chromaticities of light sources i = 1 to n.
        :n: 
            | 4 or int, optional
            | Number of source components to randomly generate when Yxyi is None.
        :pair_strengths:
            | ndarray with light source pair strengths.  
        :source_order:
            | ndarray with order of source components.
            | If None: use np.arange(n)
    
    Returns:
        :M: 
            | ndarray with fluxes.
    
    Note:
        :Algorithm:
            | 1. Loop over all source components and create intermediate sources
            |    from all (even,odd)-pairs using the relative strengths 
            |     of the pair (specified in pair_strengths). 
            | 2. Collect any remaining sources.
            | 3. Combine with new intermediate source components
            | 4. Repeat 1-3 until there are only 3 source components left. 
            | 5. Use color3mixer to calculate the required fluxes of the 3 final
            |     intermediate components to obtain the target chromaticity. 
            | 6. Backward calculate the fluxes of all original source components
            |     from the 3 final intermediate fluxes.
    """
    
    if Yxyt is None:
        Yxyt = np.atleast_2d([100,1/3,1/3])
    if Yxyi is None:
        Yxyi = np.hstack((np.ones((n,1))*100,np.random.rand(n,2)))
    else:
        n = Yxyi.shape[0]
    if pair_strengths is None:
        pair_strengths = np.random.rand(n-3)
    if source_order is None:
        source_order = np.arange(n)
        #np.random.shuffle(source_order)
        
    if n > 3:
        ps = pair_strengths.copy() # relative pair_strengths of paired sources
        so = source_order.copy() # all sources
        N_sources = so.shape[0]
        
        # Pre-initialize:
        mlut = np.nan*np.ones((2*n-3,8))
        mlut[:n,:] = np.hstack((np.arange(n)[:,None], Yxyi.copy(),\
                           np.arange(n)[:,None],np.nan*np.ones((n,1)),\
                           np.ones((n,1)),np.nan*np.ones((n,1))))
        sn_k = -np.ones(np.int(n/2), dtype = int)
        su_k = -np.ones((np.int(n/2),2),dtype = int)  
        
        k = 0   # current state counter: 
                # (states are loops runnning over all (even,odd) source component pairs.
                # After all pair intermediate sources have been made, any remaining source
                # components are collected and the state is reset running over 
                # that new list of source components. Once there are only 3 
                # source components left, color3mixer is used to calculate the
                # required fluxes to obtain the target chromaticity. The fluxes 
                # of all components are there calculate backward from the 3 fluxes.
        kk = 0 # overall counter 
        while (N_sources > 3) or (kk>n-3):
                
            # Combine two sources:
            pair_strength_AB = ps[kk]
            pA = np.int(so[2*k])
            pB = np.int(so[2*k+1])
            pAB = np.hstack((pA,pB))
            
#            xyzAB = Yxy_to_xyz(mlut[pAB,1:4])
#            YxyM = xyz_to_Yxy(pair_strength_AB * xyzAB[0,:] + (1 - pair_strength_AB) * xyzAB[1,:])[0]
        
            # About 20% faster than implementation above:
            YxyA = mlut[pA,1:4].copy()
            YxyB = mlut[pB,1:4].copy()
    
            YA = YxyA[0]
            xA = YxyA[1]
            yA = YxyA[2]
            
            YB = YxyB[0]
            xB = YxyB[1]
            yB = YxyB[2]
            
            XA = xA * YA / yA
            XB = xB * YB / yB
            ZA = (1 - xA - yA) * YA / yA
            ZB = (1 - xB - yB) * YB / yB

            XM = (pair_strength_AB * XA + (1 - pair_strength_AB) * XB)
            ZM = (pair_strength_AB * ZA + (1 - pair_strength_AB) * ZB)
            YM = (pair_strength_AB * YA + (1 - pair_strength_AB) * YB)
            xM = XM / (XM + YM + ZM)
            yM = YM / (XM + YM + ZM)
            YxyM = np.hstack((YM, xM, yM))        
        
            #plt.plot(YxyM[1],YxyM[2],'kd')
        
            #calculate the contributions of source 1 and source 2 needed to get the M of the temporary source
            MA = pair_strength_AB 
            MB = (1 - pair_strength_AB)       
            mAB = np.hstack((MA,MB))
                        
            # Do bookkeeping of components:
            sn_k[k] = n + kk
            su_k[k,:] = pAB
            
            # Store results in lut:
            mlut[n + kk,:] = np.hstack((n + kk, YxyM, pAB, mAB))

            # Get remaining components:
            rem_so = np.hstack((np.setdiff1d(so, su_k),sn_k))
            rem_so = rem_so[rem_so>=0]
            N_sources = rem_so.shape[0]
            
            # Reset source list 'so' when all pairs have been calculated for current state:
            nn = np.int(so.shape[0]/2)
            if (k == nn - 1): # update to new state
                sn_k = -np.ones(nn, dtype = int)
                su_k = -np.ones((nn,2),dtype = int)
                so = rem_so.copy()
                k = 0
            else:
                # add +1 to k:
                k += 1
            kk += 1
        
        # Calculate M3 using last 3 intermediate component sources:
        M3 = color3mixer(Yxyt,mlut[rem_so[0],1:4],mlut[rem_so[1],1:4],mlut[rem_so[2],1:4])
        M3[M3<0] = np.nan
        
        # Calculate fluxes backward from M3:
        M = np.ones((n))
        k = 0
        if not np.isnan(M3).any():
            n_min = 3 - (mlut.shape[0] - n)
            n_min = n - np.int((n_min + np.abs(n_min))/2)
            for i in np.arange(mlut.shape[0],n_min,-1)-1:
                if k < 3:
                    m3 = M3[0,-1-k]
                else:
                    m3 = 1
                pA = np.int(mlut[i,4])
                pB = mlut[i,5]
                mA = mlut[i,6]*m3
                mB = mlut[i,7]*m3
                mlut[pA,6:8] = mlut[pA,6:8]*mA
                if not np.isnan(pB):
                    pB = np.int(pB)
                    mlut[pB,6:8] = mlut[pB,6:8]*mB

                k += 1
            M = mlut[:n,6]
        else:
            M = np.nan*M

    else: # Use fast color3mixer
        
        M = color3mixer(Yxyt,Yxyi[0,:],Yxyi[1,:],Yxyi[2,:])

    return np.atleast_2d(M)


#------------------------------------------------------------------------------
def get_w_summed_spd(w,spds):
    """
    Calculate weighted sum of spds.
    
    Args:
        :w: 
            | ndarray with weigths (e.g. fluxes)
        :spds: 
            | ndarray with component spds.
        
    Returns:
        :returns: 
            | ndarray with weighted sum.
    """
    return np.vstack((spds[0],np.dot(np.abs(w),spds[1:])))


#------------------------------------------------------------------------------
def fitnessfcn(x, spd_constructor, spd_constructor_pars = None, F_rss = True, decimals = [3], obj_fcn = [None], obj_fcn_pars = [{}], obj_fcn_weights = [1], obj_tar_vals = [0], verbosity = 0, out = 'F'):
    """
    Fitness function that calculates closeness of solution x to target values 
    for specified objective functions.
    
    Args:
        :x: 
            | ndarray with parameter values
        :spd_constructor:
            | function handle to a function that constructs the spd
              from parameter values in :x:.
        :spd_constructor_pars:
            | None, optional,
            | Parameters required by :spd_constructor:
        :F_rss:
            | True, optional
            | Take Root-Sum-of-Squares of 'closeness' values between target and 
              objective function values.
        :decimals:
            | 3, optional
            | Rounding decimals of objective function values.
        :obj_fcn: 
            | [None] or list, optional
            | Function handles to objective function.
        :obj_fcn_weights:
            | [1] or list, optional.
            | Weigths for each obj. fcn
        :obj_fcn_pars:
            | [None] or list, optional
            | Parameter dicts for each obj. fcn.
        :obj_tar_vals:
            | [0] or list, optional
            | Target values for each objective function.
        :verbosity:
            | 0, optional
            | If > 0: print intermediate results.
        :out: 
            | 'F', optional
            | Determines output.
            
    Returns:
        :F:
            | float or ndarray with fitness value for current solution :x:.
    """
    
    # Keep track of solutions tried:
    global optcounter 
    optcounter = optcounter + 1
    
    # Number of objective functions:
    N = len(obj_fcn)
    
    # Get current spdi:
    spdi,args_out,component_spds = spd_constructor(x,spd_constructor_pars) 

    # Goodness-of-fit:
    F = np.nan*np.ones((N))
    obj_vals = F.copy()
    
    if np.isnan(spdi[1:].sum()):
        F = 10000000*np.ones(F.shape)

    else:
        
        # Make decimals and obj_fcn_weights same size as N:
        decimals =  decimals*np.ones((N))
        obj_fcn_weights =  obj_fcn_weights*np.ones((N))
        obj_fcn_pars = np.asarray(obj_fcn_pars*N)
        obj_tar_vals = np.asarray(obj_tar_vals)
        
        # Calculate all objective functions and closeness to target values
        # store squared weighted differences for speed:
        output_str = 'c{:1.0f}: F = {:1.' + '{:1.0f}'.format(decimals.max()) + 'f}' + ' : '

        for i in range(N):
            if obj_fcn[i] is not None:
                obj_vals[i] = obj_fcn[i](spdi, **obj_fcn_pars[i])
                
                if obj_tar_vals[i] > 0:
                    f_normalize = obj_tar_vals[i]
                else:
                    f_normalize = 1
                    
                F[i] = (obj_fcn_weights[i]*(np.abs((np.round(obj_vals[i],np.int(decimals[i])) - obj_tar_vals[i])/f_normalize)**2))
                
                if (verbosity > 0):
                    output_str = output_str + r' obj_#{:1.0f}'.format(i+1) + ' = {:1.' + '{:1.0f}'.format(np.int(decimals[i])) + 'f},'
            else:
                obj_vals[i] = np.nan
                F[i] = np.nan
    
        # Print intermediate results:
        if (verbosity > 0):
            print(output_str.format(*np.hstack((optcounter, np.sqrt(np.nansum(F)), obj_vals))))
    
    # Take Root-Sum-of-Squares of delta((val - tar)**2):
    if F_rss == True:
        F = np.sqrt(np.nansum(F))

    
    if out == 'F':
        return F
    elif out == 'args_out':
        return args_out
    elif out == 'obj_vals':
        return obj_vals
    elif out == 'F,obj_vals':
        return F, obj_vals
    elif out == 'spdi,obj_vals':
        return spdi, obj_vals
    elif out == 'spdi,args_out':
        return spdi, args_out
    elif out == 'spdi,args_out,component_spds':
        return spdi, args_out, component_spds
    elif out == 'spdi,obj_vals,args_out':
        return spdi,obj_vals,args_out
    elif out == 'spdi,obj_vals,args_out,component_spds':
        return spdi,obj_vals,args_out,component_spds
    else:
        eval(out)
        


def spd_constructor_2(x, constructor_pars = {}, **kwargs):
    """
    Construct spd from model parameters using pairs of intermediate sources.
    
    | Pairs (odd,even) of components are selected and combined using 
      'pair_strength'. This process is continued until only 3 intermediate 
      (combined) sources remain. Color3mixer is then used to calculate the 
      fluxes for the remaining 3 sources, after which the fluxes of all 
      components are back-calculated.
    
    Args:
        :x: 
            | vector of optimization parameters.
        :constructor_pars: 
            | dict with model parameters. 
            | Key 'list' determines which parameters are in :x: and key 'len'
              (Specifies the number of variables representing each parameter).
        
    Returns:
        :returns: 
            | spd, M, spds
            | ndarrays with spectrum corresponding to x, M the fluxes of 
              the spectral components of spd and spds the spectral components 
              themselves.
    
    """
    cp = constructor_pars.copy()
        
    # replace / init cp with values from x (parameters to optimize)
    # (opt_list and opt_len refer resp. to the key in cp and the length
    # of that parameter in x)
    cp, vsize = vec_to_dict(vec= x, dic = cp, vsize = cp['len'], keys = cp['list'])

    spd,M,component_spds = spd_builder(peakwl = cp['peakwl'], fwhm = cp['fwhm'],\
                                      bw_order = cp['bw_order'],\
                                       pair_strengths = cp['pair_strengths'],\
                                      strength_shoulder = cp['strength_shoulder'],\
                                      target = cp['target'], tar_type = cp['tar_type'],\
                                      cspace_bwtf = cp['cspace_bwtf'], cieobs = cp['cieobs'],\
                                      use_piecewise_fcn = cp['use_piecewise_fcn'], wl = cp['wl'],\
                                      component_spds = cp['component_spds'],\
                                      strength_ph = None,\
                                      peakwl_ph1 = None, fwhm_ph1 = None, strength_ph1 = None,\
                                      peakwl_ph2 = None, fwhm_ph2 = None, strength_ph2 = None,\
                                      flux = None, with_wl = True, verbosity = 0, out = 'spd,M,component_spds',**kwargs)
   
    spds = np.squeeze(component_spds.T, axis = 2)
    spds = np.vstack((spd[0],spds)) # store component spectra in spds with first axis components, second axis wavelengths

    # Calculate  SPD:
    spd = get_w_summed_spd(M, spds)
    
    return spd,M,spds



def spd_constructor_3(x, constructor_pars = {}, **kwargs):
    """
    Construct spd from model parameters using trio's of intermediate sources.
    
    
    | The triangle/trio method creates for all possible combinations of 3 primary
      component spectra a spectrum that results in the target chromaticity 
      using color3mixer() and then optimizes the weights of each of the latter 
      spectra such that adding them (additive mixing) results in obj_vals as 
      close as possible to the target values.
    
    Args:
        :x:
            | vector of optimization parameters.
        :constructor_pars:
            | dict with model parameters. 
            | Key 'list' determines which parameters are in :x: and key 'len'
              (specifies the number of variables representing each parameter).
        
    Returns:
        :returns: 
            | spd, M, spds
            | ndarrays with spectrum corresponding to x, M the fluxes of 
              the spectral components of spd and spds the spectral components 
              themselves.
    
    """
    cp = constructor_pars.copy()
    
    # replace / init cp with values from x (parameters to optimize)
    # (opt_list and opt_len refer resp. to the key in cp and the length
    # of that parameter in x)
    cp, vsize = vec_to_dict(vec= x, dic = cp, vsize = cp['len'], keys = cp['list'])

    target = None #only calculate component spectra
    Yxy_target = cp['target']
    spd, component_spds = spd_builder(peakwl = cp['peakwl'], fwhm = cp['fwhm'],\
                                      bw_order = cp['bw_order'],\
                                      pair_strengths = cp['pair_strengths'],\
                                      strength_shoulder = cp['strength_shoulder'],\
                                      target = target, tar_type = cp['tar_type'],\
                                      cspace_bwtf = cp['cspace_bwtf'], cieobs = cp['cieobs'],\
                                      use_piecewise_fcn = cp['use_piecewise_fcn'], wl = cp['wl'],\
                                      component_spds = cp['component_spds'],\
                                      strength_ph = None,\
                                      peakwl_ph1 = None, fwhm_ph1 = None, strength_ph1 = None,\
                                      peakwl_ph2 = None, fwhm_ph2 = None, strength_ph2 = None,\
                                      flux = None,with_wl = True, verbosity = 0, out = 'spd,component_spds',**kwargs)
    
    spds = spd # component spds in Nxwl format
    
    # Calculate xyzi and Yxyi of component spectra:
    xyzi = spd_to_xyz(spds, relative = False, cieobs = cieobs)
    Yxyi = xyz_to_Yxy(xyzi)

    # Generate all possible 3-channel combinations (component triangles):
    N = Yxyi.shape[0]
    combos = np.array(list(itertools.combinations(range(N), 3))) 
   
    # calculate fluxes to obtain target Yxyt:
    M3 = color3mixer(Yxy_target,Yxyi[combos[:,0],:],Yxyi[combos[:,1],:],Yxyi[combos[:,2],:])
        
    # Get rid of out-of-gamut solutions:
    is_out_of_gamut =  (((M3<0).sum(axis=1))>0)
    M3[is_out_of_gamut,:] = 0
    Nc = combos.shape[0]
    
    M3[is_out_of_gamut,:] = np.nan
    if Nc > 1:
        # Calulate fluxes of all components from M3 and x_final:            
        M_final = cp['triangle_strengths'][:,None]*M3
        M = np.empty((N))
        for i in range(N):
            M[i] = np.nansum(M_final[np.where(combos == i)])
    else:
        M = M3
    
    # Calculate optimized SPD:
    spd = get_w_summed_spd(M, spds)
    
    # When all out-of-gamut: set spd to NaN's:
    if sum(M) == 0:
        spd[1:,:] = np.nan
        
    return spd,M,spds

#------------------------------------------------------------------------------
def spd_optimizer_2_3(optimizer_type = '2mixer', \
                    spd_constructor = None, spd_model_pars = None,\
                    component_data = 4, N_components = None, wl = _WL3,\
                    allow_butterworth_mono_spds = False,\
                    Yxy_target = np2d([100,1/3,1/3]), cieobs = _CIEOBS,\
                    obj_fcn = [None], obj_fcn_pars = [{}], obj_fcn_weights = [1],\
                    obj_tar_vals = [0], decimals = [5], \
                    minimize_method = 'nelder-mead', minimize_opts = None, F_rss = True,\
                    verbosity = 0,**kwargs):
    """
    Optimizes the weights (fluxes) of a set of component spectra by combining 
    pairs (2) or trio's (3) of components to intermediate sources until only 3
    remain. Color3mixer can then be called to calculate required fluxes to
    obtain target chromaticity and fluxes are then back-calculated.
         
    Args:
        :optimizer_type: 
            | '2mixer' or '3mixer' or 'user', optional
            | Specifies whether to optimize spectral model parameters by 
              combining pairs or trio's of comonponents.
        :spd_constructor: 
            | None, optional
            | Function handle to user defined spd_constructor function.
            |     Input: fcn(x, constructor_pars = {}, kwargs)
            |     Output: spd,M,spds
            |         nd array with:
            |             - spd: spectrum resulting from x
            |            - M: fluxes of all component spds
            |             - spds: component spds (in [N+1,wl] format)
            | (See e.g. spd_constructor_2 or spd_constructor_3)
        :spd_model_pars: 
            | dict with model parameters required by spd_constructor
              and with optimization parameters required by minimize (x0, lb, ub).                .
            | Only used when :optimizer_type: == 'user'.
        :component_data:
            | 4, optional
            | Component spectra data: 
            | If int: specifies number of components used in optimization 
            |         (peakwl, fwhm and pair_strengths will be optimized).
            | If dict: generate components based on parameters (peakwl, fwhm, 
            |          pair_strengths, etc.) in dict. 
            |         (keys with None values will be optimized)
            | If ndarray: optimize pair_strengths of component spectra.
        :N_components:
            | None, optional
            | Specifies number of components used in optimization. (only used 
              when :component_data: is dict and user wants to override dict. 
            | Note that shape of parameters arrays must match N_components).
        :allow_butterworth_mono_spds: 
            | False, optional
            | False: use pure Gaussian based monochrom. spds.
        :wl:
            | _WL3, optional
            | Wavelengths used in optimization when :component_data: is not 
            | ndarray with spectral data.

        :Yxy_target:
            | np2d([100,1/3,1/3]), optional
            | ndarray with Yxy chromaticity of target.
        :cieobs:
            | _CIEOBS, optional
            | CIE CMF set used to calculate chromaticity values if not provided 
              in :Yxyi:.
        :F_rss: 
            | True, optional
            | Take Root-Sum-of-Squares of 'closeness' values between target and 
              objective function values.
        :decimals:
            | 5, optional
            | Rounding decimals of objective function values.
        :obj_fcn: 
            | [None] or list, optional
            | Function handles to objective function.
        :obj_fcn_weights:
            | [1] or list, optional.
            | Weigths for each obj. fcn
        :obj_fcn_pars:
            | [None] or list, optional
            | Parameter dicts for each obj. fcn.
        :obj_tar_vals:
            | [0] or list, optional
            | Target values for each objective function.
        :minimize_method:
            | 'nelder-mead', optional
            | Optimization method used by minimize function.
        :minimize_opts: 
            | None, optional
            | Dict with minimization options. 
            | None defaults to: {'xtol': 1e-5, 'disp': True, 'maxiter': 1000*Nc,
            |                     'maxfev' : 1000*Nc,'fatol': 0.01}
        :verbosity:
            | 0, optional
            | If > 0: print intermediate results.
            
    Returns:
        :returns:
            | M, spd_opt, obj_vals
            |   - 'M': ndarray with fluxes for each component spectrum.
            |   - 'spd_opt': optimized spectrum.
            |   - 'obj_vals': values of the obj. fcns for the optimized spectrum.
    """

    # Set spd_constructor function:
    if optimizer_type == '2mixer':
        spd_constructor = spd_constructor_2
    elif optimizer_type == '3mixer':
        spd_constructor = spd_constructor_3
    elif optimizer_type == 'search': # Optimize fluxes and component model parameters (chromaticity is part of obj_fcn list)
        raise Exception("spd_optimizer_2_3(): optimizer_type = 'search' not yet implemented. Use '2mixer' or '3mixer'. ")
    elif optimizer_type == 'user':
        if spd_constructor is None:
            raise Exception('spd_to_optimizer_2_3(): No user defined spd_constructor found.')
    
    # Initialize  spd_model_pars and spd_optim_pars:
    if optimizer_type != 'user':
        spd_optim_pars, spd_model_pars = initialize_spd_optim_pars(component_data, \
                                                                   optimizer_type = optimizer_type, \
                                                                   allow_butterworth_mono_spds = allow_butterworth_mono_spds, \
                                                                   wl = wl)        
        spd_model_pars = {**spd_model_pars, **spd_optim_pars} # merge two dicts
    else:
        if 'x0' not in spd_model_pars:
            spd_optim_pars['x0'] = None
        if 'LB' not in spd_model_pars:
            spd_optim_pars['LB'] = None
        if 'UB' not in spd_model_pars:
            spd_optim_pars['UB'] = None
            
    # Also store the following args in spd_constructor_pars (needed by spd_constructor):
    spd_model_pars['target'] = Yxy_target
    spd_model_pars['tar_type'] = 'Yxy'
    spd_model_pars['cspace_bwtf'] = {}
    spd_model_pars['cieobs'] = cieobs
    
    # Get starting value, lower and upper bounds:
    x0 = spd_optim_pars['x0']
    bounds = (spd_optim_pars['LB'], spd_optim_pars['UB'])

    # Setup optimization:
    global optcounter
    optcounter = 1     

    if minimize_opts is None:
        minimize_opts = {'xtol': 1e-5, 'disp': True, 'maxiter' : 1000*len(x0), 'maxfev' : 1000*len(x0),'fatol': 0.01}
    input_par = ('F', spd_constructor, spd_model_pars, obj_fcn, obj_fcn_pars, obj_fcn_weights, obj_tar_vals, F_rss, decimals, verbosity)
      
    # Create positional argument only function for scipy.minimize():
    def fit_fcn(x, out, spd_constructor, spd_model_pars,  obj_fcn, obj_fcn_pars, obj_fcn_weights, obj_tar_vals, F_rss, decimals, verbosity):
        F = fitnessfcn(x, spd_constructor, spd_constructor_pars = spd_model_pars,\
                  F_rss = F_rss, decimals = decimals,\
                  obj_fcn = obj_fcn, obj_fcn_pars = obj_fcn_pars, obj_fcn_weights = obj_fcn_weights,\
                  obj_tar_vals = obj_tar_vals, verbosity = verbosity, out = out)
        return F

    # Perform optimzation:
    res = math.minimizebnd(fit_fcn, x0, args = input_par, method = minimize_method, use_bnd = True, bounds = bounds , options = minimize_opts)
    x_final = np.abs(res['x'])
   
    # Calculate optimized SPD and get obj_vals and fluxes:
    spd_opt, obj_vals, M, component_spds = fit_fcn(x_final, 'spdi,obj_vals,args_out,component_spds', spd_constructor, spd_model_pars, obj_fcn, obj_fcn_pars, obj_fcn_weights, obj_tar_vals, F_rss, decimals, verbosity)
    
    res['obj_vals'] = obj_vals
    res['x_final'] = x_final
    res['spd_opt'] = spd_opt
    res['M'] = M
    res['component_spds'] = component_spds
    
    return spd_opt, M, component_spds, obj_vals, res
        

#------------------------------------------------------------------------------
def get_optim_pars_dict(target = np2d([100,1/3,1/3]), tar_type = 'Yxy', cieobs = _CIEOBS,\
              optimizer_type = '2mixer', spd_constructor = None, spd_model_pars = None,\
              cspace = 'Yuv', cspace_bwtf = {}, cspace_fwtf = {},\
              component_spds = None, N_components = None,\
              obj_fcn = [None], obj_fcn_pars = [{}], obj_fcn_weights = [1],\
              obj_tar_vals = [0], decimals = [5], \
              minimize_method = 'nelder-mead', minimize_opts = None, F_rss = True,\
              peakwl = [450,530,610], fwhm = [20,20,20], \
              allow_butterworth_mono_spds = False, bw_order = [-1],\
              wl = _WL3, with_wl = True, strength_shoulder = 2,\
              strength_ph = [0], use_piecewise_fcn = False,\
              peakwl_ph1 = [530], fwhm_ph1 = [80], strength_ph1 = [1],\
              peakwl_ph2 = [560], fwhm_ph2 = [80], strength_ph2 = None,\
              verbosity = 0,\
              pair_strengths = None,triangle_strengths = None,\
              peakwl_min = [400], peakwl_max = [700],\
              fwhm_min = [5], fwhm_max = [300],\
              bw_order_min = [0], bw_order_max = [100]):
    """
    Setup dict with optimization parameters.
    
    
    Args:
        See  ?spd_optimizer for more info. 
        
    Returns:
        :opts: 
            | dict with keys and values of the function's keywords and values.
    """
    opts = locals()
    spd_models_pars = opts.pop('spd_model_pars')
    
    
    # Set number of component sources:
    if component_spds is not None:
        N_components = component_spds.shape[0] - 1
    if N_components is None:
        N_components = len(peakwl)
    if N_components < 3:
        raise Exception('optim_dict(): Optimization requires at least 3 component sources.')

    
    # Ensure sufficient length of peakw if input comes from component_spds or N_components:
    if len(fwhm) < N_components:
        fwhm = (wl[-1]-wl[0])/(N_components-1)*np.ones(N_components)
        if fwhm[0] < min(fwhm_min):
            fwhm = min(fwhm_min)*np.ones(N_components)
    if len(peakwl) < N_components:
        dd = (max(peakwl_max)-min(peakwl_min))/(1*N_components)
        peakwl = np.linspace(min(peakwl_min)+dd, max(peakwl_max)-dd, N_components)
    if allow_butterworth_mono_spds == True:
        if len(bw_order) < N_components:
            bw_order = min(bw_order_min)*np.ones(N_components)
    
    # Set max and min values:
    if len(peakwl_min) != len(peakwl):
        peakwl_min = min(peakwl_min)*np.ones(N_components)
        peakwl = [max([peakwl_min[i],peakwl[i]]) for i in range(N_components)] #ensure values are within bounds

    if len(peakwl_max) != len(peakwl):
        peakwl_max = max(peakwl_max)*np.ones(N_components)
        peakwl = [min([peakwl_max[i],peakwl[i]]) for i in range(N_components)] #ensure values are within bounds

    if len(fwhm_min) != len(fwhm):
        fwhm_min = min(fwhm_min)*np.ones(N_components)
        fwhm = [max([fwhm_min[i],fwhm[i]]) for i in range(N_components)] #ensure values are within bounds

    if len(fwhm_max) != len(fwhm):
        fwhm_max = max(fwhm_max)*np.ones(N_components)
        fwhm = [min([fwhm_max[i],fwhm[i]]) for i in range(N_components)] #ensure values are within bounds
    
    if allow_butterworth_mono_spds == True: # do nothing, no butterworth profile requested
        bw_order = np.atleast_2d(bw_order) # convert to ndarray for boolean slicing
        bw_order[bw_order == -1] = 0 #0 also results in pure gaussian
        bw_order = bw_order.tolist()[0] # convert back to list for normal processing
        if (len(bw_order_max) != len(bw_order)):
            bw_order_max = max(bw_order_max)*np.ones(N_components)
            bw_order = [min([bw_order_max[i],np.abs(bw_order[i])]) for i in range(N_components)] #ensure values are within bounds

        if (len(bw_order_min) != len(bw_order)):
            bw_order_min = min(bw_order_min)*np.ones(N_components)
            bw_order = [max([bw_order_min[i],np.abs(bw_order[i])]) for i in range(N_components)] #ensure values are within bounds
            
    else:
        bw_order = -1


    #store in dict:
    opts['list'] = []
    opts['len'] = []
    opts['peakwl'] = peakwl
    opts['peakwl_min'] = peakwl_min
    opts['peakwl_max'] = peakwl_max
    opts['fwhm'] = fwhm
    opts['fwhm_min'] = fwhm_min
    opts['fwhm_max'] = fwhm_max
    opts['bw_order'] = bw_order
    opts['bw_order_min'] = bw_order_min
    opts['bw_order_max'] = bw_order_max
    opts['allow_butterworth_mono_spds'] = allow_butterworth_mono_spds
    
    # Generate random set of pair_strengths (for '2mixer'):
    if pair_strengths is None:
        opts['pair_strengths'] = np.random.rand(N_components-3)
    else:
        opts['pair_strengths'] = pair_strengths

    # Generate random set of triangle_strengths (for '3mixer'):
    if triangle_strengths is None:
        combos = np.array(list(itertools.combinations(range(N_components), 3))) 
        opts['triangle_strengths'] = np.random.rand(combos.shape[0])
    else:
        opts['triangle_strengths'] = triangle_strengths

    return opts


def initialize_spd_model_pars(component_data, N_components = None, allow_butterworth_mono_spds = False, optimizer_type = '2mixer', wl = _WL3):
    """
    Initialize spd_model_pars dict (for spd_constructor) based on type 
    of component_data.
    
    Args:
        :component_data: 
            | None, optional
            | Component spectra data: 
            | If int: specifies number of components used in optimization 
            |         (peakwl, fwhm and pair_strengths will be optimized).
            | If dict: generate components based on parameters (peakwl, fwhm, 
            |          pair_strengths, etc.) in dict. 
            |         (keys with None values will be optimized)
            | If ndarray: optimize pair_strengths of component spectra.
        :N_components: 
            | None, optional
            | Specifies number of components used in optimization. (only used 
            | when :component_data: is dict and user wants to override dict. 
            | Note that shape of parameters arrays must match N_components).
        :allow_butterworth_mono_spds:
            | False, optional
            |  - False: use pure Gaussian based monochrom. spds.
            |  - True: also allow butterworth type monochrom. spds while optimizing.
        :optimizer_type:
            | '2mixer', optional
            | Type of spectral optimization routine.
            | (other options: '3mixer', 'search')
        :wl: 
            | _WL3, optional
            | Wavelengths used in optimization when :component_data: is not an
              ndarray with spectral data.
        
    Returns:
        :spd_model_pars: 
            | dict with spectrum-model parameters

    """
    # Initialize parameter dict:
    if isinstance(component_data,int):
        # input is Number of components
        N = component_data
        spd_model_pars = get_optim_pars_dict(N_components = N, allow_butterworth_mono_spds = allow_butterworth_mono_spds)
        spd_model_pars['N_components'] = N
        spd_model_pars['component_spds'] = None
        
        spd_model_pars['fluxes'] = np.ones(N)
        spd_model_pars['peakwl'] = np.linspace(min(spd_model_pars['peakwl_min']),max(spd_model_pars['peakwl_max']),N)
        spd_model_pars['fwhm'] = (wl[-1]-wl[0])/(N-1)*np.ones(N)
        if spd_model_pars['fwhm'][0] < min(spd_model_pars['fwhm_min']):
            spd_model_pars['fwhm'] = min(spd_model_pars['fwhm_min'])*np.ones(N)
        
        # Generate list with optimization parameters:    
        spd_model_pars['list'] = ['peakwl','fwhm']
        spd_model_pars['len'] = [N, N]  
        
        # Also use butterworth spd profiles, instead of only gaussians:
        if allow_butterworth_mono_spds == True:
            spd_model_pars['bw_order'] = np.ones(N)
            spd_model_pars['list'].append('bw_order')
            spd_model_pars['len'].append(N)
        spd_model_pars['allow_butterworth_mono_spds'] = allow_butterworth_mono_spds           
                    
        # Overwrite with input args:
        spd_model_pars['wl'] = wl
        
    elif isinstance(component_data,dict):
        # input is dict with component parameters:
        spd_model_pars = component_data.copy()
        
        if N_components is not None:
            N = N_components
        else:
            N = spd_model_pars['N_components']
        
        spd_model_pars['N_components'] = N
        spd_model_pars['component_spds'] = None
        spd_model_pars['list'] = []
        spd_model_pars['len'] = []
        
        if component_data['peakwl'] is None:
            spd_model_pars['list'].append('peakwl')
            spd_model_pars['len'].append(N)
         
        if component_data['fwhm'] is None:
            spd_model_pars['list'].append('fwhm')    
            spd_model_pars['len'].append(N)
            
        if spd_model_pars['allow_butterworth_mono_spds'] == True:
            if component_data['bw_order'] is None:
                spd_model_pars['list'].append('bw_order')    
                spd_model_pars['len'].append(N)
         
        # Overwrite with input args:
        spd_model_pars['wl'] = wl
 
    
    else:
        # input is ndarray with component spectra
        spd_model_pars = get_optim_pars_dict(component_spds = component_data)
        N = component_data.shape[0] - 1
        spd_model_pars['N_components'] = N
        spd_model_pars['component_spds'] = component_data        
        
        # store input args:
        spd_model_pars['wl'] = component_data[0]
     
    
    # Append pair ot triangle_strengths to opt_list and opt_len:      
    if optimizer_type == '2mixer':
        spd_model_pars['list'].append('pair_strengths')
        spd_model_pars['len'].append(N-3)
    
    elif optimizer_type =='3mixer':
        spd_model_pars['list'].append('triangle_strengths')
        spd_model_pars['len'].append(spd_model_pars['triangle_strengths'].shape[0])
           
    return spd_model_pars

def initialize_spd_optim_pars(component_data, N_components = None,\
                              allow_butterworth_mono_spds = False,\
                              optimizer_type = '2mixer', wl = _WL3):
    """
    Initialize spd_optim_pars dict based on type of component_data.
    
    Args:
        :component_data: 
            | None, optional
            | Component spectra data: 
            | If int: specifies number of components used in optimization 
            |         (peakwl, fwhm and pair_strengths will be optimized).
            | If dict: generate components based on parameters (peakwl, fwhm, 
            |          pair_strengths, etc.) in dict. 
            |         (keys with None values will be optimized)
            | If ndarray: optimize pair_strengths of component spectra.
        :N_components:
            | None, optional
            | Specifies number of components used in optimization. (only used 
              when :component_data: is dict and user wants to override dict. 
            | Note that shape of parameters arrays must match N_components).
        :allow_butterworth_mono_spds: 
            | False, optional
            | False: use pure Gaussian based monochrom. spds.
        :optimizer_type: 
            | '2mixer', optional
            | Type of spectral optimization routine.
              (other options: '3mixer', 'search')
        :wl:
            | _WL3, optional
            | Wavelengths used in optimization when :component_data: is not an
              ndarray with spectral data.
        
    Returns:
        :spd_optim_pars:
            | dict with optimization parameters (x0, ub, lb)

    """
    spd_optim_pars = {}
    spd_model_pars = initialize_spd_model_pars(component_data, N_components = N_components,\
                                               optimizer_type = optimizer_type, \
                                               allow_butterworth_mono_spds = allow_butterworth_mono_spds, wl = wl)
    N = spd_model_pars['N_components']

    # Initialize parameter dict:
    if isinstance(component_data,int):      
        # Generate LB, UB, x0 (keys in opt_list):
        spd_optim_pars['LB'] = np.hstack((spd_model_pars['peakwl_min'], spd_model_pars['fwhm_min']))
        spd_optim_pars['UB'] = np.hstack((spd_model_pars['peakwl_max'], spd_model_pars['fwhm_max']))
        spd_optim_pars['x0'] = np.hstack((spd_model_pars['peakwl'], spd_model_pars['fwhm']))
        
        if allow_butterworth_mono_spds == True:
            spd_optim_pars['LB'] = np.hstack((spd_optim_pars['LB'],spd_model_pars['bw_order_min']))
            spd_optim_pars['UB'] = np.hstack((spd_optim_pars['UB'],spd_model_pars['bw_order_max']))
            spd_optim_pars['x0'] = np.hstack((spd_optim_pars['x0'],spd_model_pars['bw_order']))

        
        if optimizer_type == '2mixer':
            spd_optim_pars['LB'] = np.hstack((spd_optim_pars['LB'],np.zeros(N-3)))
            spd_optim_pars['UB'] = np.hstack((spd_optim_pars['UB'],np.ones(N-3)))
            spd_optim_pars['x0'] = np.hstack((spd_optim_pars['x0'],spd_model_pars['pair_strengths']))

        elif optimizer_type == '3mixer':
            spd_optim_pars['LB'] = np.hstack((spd_optim_pars['LB'],np.zeros(spd_model_pars['triangle_strengths'].shape[0])))
            spd_optim_pars['UB'] = np.hstack((spd_optim_pars['UB'],np.ones(spd_model_pars['triangle_strengths'].shape[0])))
            spd_optim_pars['x0'] = np.hstack((spd_optim_pars['x0'],spd_model_pars['triangle_strengths']))
        
    elif isinstance(component_data,dict):
        # input is dict with component parameters:
        spd_optim_pars['LB'] = []
        spd_optim_pars['UB'] = []
        spd_optim_pars['x0'] = []
        
        if component_data['peakwl'] is None:
            spd_optim_pars['LB'].append(spd_model_pars['peakwl_min'])
            spd_optim_pars['UB'].append(spd_model_pars['peakwl_max'])
            spd_optim_pars['x0'].append(list(np.linspace(min(spd_model_pars['peakwl_min']),max(spd_model_pars['peakwl_max']),N)))
        
        if component_data['fwhm'] is None:
            spd_optim_pars['LB'].append(spd_model_pars['fwhm_min'])
            spd_optim_pars['UB'].append(spd_model_pars['fwhm_max'])
            fwhm_ = (wl[-1]-wl[0])/(N-1)*np.ones(N)
            if fwhm_[0] < min(spd_model_pars['fwhm_min']):
                fwhm_ = min(spd_model_pars['fwhm_min'])*np.ones(N)
            spd_optim_pars['x0'].append(list(fwhm_))
        
        if allow_butterworth_mono_spds == True:
            spd_optim_pars['LB'].append(spd_model_pars['bw_order_min'])
            spd_optim_pars['UB'].append(spd_model_pars['bw_order_max'])
            spd_optim_pars['x0'].append(spd_model_pars['bw_order'])

        
        if optimizer_type == '2mixer':
            spd_optim_pars['LB'].append(list(np.zeros(N-3)))
            spd_optim_pars['UB'] .append(list(np.ones(N-3)))
            spd_optim_pars['x0'].append(spd_model_pars['pair_strengths'])
        
        elif optimizer_type == '3mixer':
            spd_optim_pars['LB'].append(list(np.zeros(spd_model_pars['triangle_strengths'].shape[0])))
            spd_optim_pars['UB'].append(list(np.ones(spd_model_pars['triangle_strengths'].shape[0])))
            spd_optim_pars['x0'].append(spd_model_pars['triangle_strengths'])

    else:
        # input is ndarray with component spectra
        if optimizer_type == '2mixer':
            spd_optim_pars['LB'] =  np.zeros(N-3)
            spd_optim_pars['UB'] =  np.ones(N-3)
            spd_optim_pars['x0'] =  spd_model_pars['pair_strengths'].copy()
        
        elif optimizer_type =='3mixer':
            spd_optim_pars['LB'] =  np.zeros(spd_model_pars['triangle_strengths'].shape[0])
            spd_optim_pars['UB'] =  np.ones(spd_model_pars['triangle_strengths'].shape[0])
            spd_optim_pars['x0'] =  spd_model_pars['triangle_strengths'].copy()
    

    return spd_optim_pars, spd_model_pars

            
#------------------------------------------------------------------------------
def spd_optimizer(target = np2d([100,1/3,1/3]), tar_type = 'Yxy', cieobs = _CIEOBS,\
                  optimizer_type = '2mixer', spd_constructor = None, spd_model_pars = None,\
                  cspace = 'Yuv', cspace_bwtf = {}, cspace_fwtf = {},\
                  component_spds = None, N_components = None,\
                  obj_fcn = [None], obj_fcn_pars = [{}], obj_fcn_weights = [1],\
                  obj_tar_vals = [0], decimals = [5], \
                  minimize_method = 'nelder-mead', minimize_opts = None, F_rss = True,\
                  peakwl = [450,530,610], fwhm = [20,20,20], \
                  allow_butterworth_mono_spds = False, bw_order = [-1],\
                  wl = _WL3, with_wl = True, strength_shoulder = 2,\
                  strength_ph = [0], use_piecewise_fcn = False,\
                  peakwl_ph1 = [530], fwhm_ph1 = [80], strength_ph1 = [1],\
                  peakwl_ph2 = [560], fwhm_ph2 = [80], strength_ph2 = None,\
                  verbosity = 0,\
                  pair_strengths = None,\
                  peakwl_min = [400], peakwl_max = [700],\
                  fwhm_min = [5], fwhm_max = [300],\
                  bw_order_min = 0, bw_order_max = 100):
    """
    Generate a spectrum with specified white point and optimized for certain 
    objective functions from a set of component spectra or component spectrum 
    model parameters.
    
    Args:
        :target: 
            | np2d([100,1/3,1/3]), optional
            | ndarray with Yxy chromaticity of target.
        :tar_type:
            | 'Yxy' or str, optional
            | Specifies the input type in :target: (e.g. 'Yxy' or 'cct')
        :cieobs:
            | _CIEOBS, optional
            | CIE CMF set used to calculate chromaticity values, if not provided 
              in :Yxyi:.
        :optimizer_type:
            | '2mixer',  optional
            | Specifies type of chromaticity optimization 
            | ('3mixer' or '2mixer' or 'search')
            | For help on '2mixer' and '3mixer' algorithms, see notes below.
        :spd_constructor:
            | None, optional
            | Function handle to user defined spd_constructor function.
            |     Input: fcn(x, constructor_pars = {}, kwargs)
            |     Output: spd,M,spds
            |         nd array with:
            |             - spd: spectrum resulting from x
            |             - M: fluxes of all component spds
            |             - spds: component spds (in [N+1,wl] format)
            | (See e.g. spd_constructor_2 or spd_constructor_3)
        :spd_model_pars:
            | dict with model parameters required by spd_constructor
              and with optimization parameters required by minimize (x0, lb, ub).                .
            | Only used when :optimizer_type: == 'user'.
        :cspace:
            | 'Yuv', optional
            | Color space for 'search'-type optimization. 
        :cspace_bwtf:
            | {}, optional
            | Backward (cspace_to_xyz) transform parameters 
            | (see colortf()) to go from :tar_type: to 'Yxy').
        :cspace_fwtf:
            | {}, optional
            | Forward (xyz_to_cspace) transform parameters 
            | (see colortf()) to go from xyz to :cspace:).
        :component_spds:
            | ndarray of component spectra.
            | If None: they are built from input args.
        :N_components:
            | None, optional
            | Specifies number of components used in optimization. (only used 
              when :component_data: is dict and user wants to override dict value
            | Note that shape of parameters arrays must match N_components).
        :allow_butterworth_mono_spds:
            | False, optional
            | False: use pure Gaussian based monochrom. spds.
        :wl: 
            | _WL3, optional
            | Wavelengths used in optimization when :component_data: is not an
              ndarray with spectral data.
        :F_rss: 
            | True, optional
            | Take Root-Sum-of-Squares of 'closeness' values between target and 
              objective function values.
        :decimals:
            | 5, optional
            | Rounding decimals of objective function values.
        :obj_fcn: 
            | [None] or list, optional
            | Function handles to objective function.
        :obj_fcn_weights:
            | [1] or list, optional.
            | Weigths for each obj. fcn
        :obj_fcn_pars:
            | [None] or list, optional
            | Parameter dicts for each obj. fcn.
        :obj_tar_vals:
            | [0] or list, optional
            | Target values for each objective function.
        :minimize_method:
            | 'nelder-mead', optional
            | Optimization method used by minimize function.
        :minimize_opts:
            | None, optional
            | Dict with minimization options. 
            |  None defaults to: {'xtol': 1e-5, 'disp': True, 'maxiter': 1000*Nc,
            |                     'maxfev' : 1000*Nc,'fatol': 0.01}
        :verbosity:
            | 0, optional
            | If > 0: print intermediate results.
         
    Note:
        peakwl:, :fwhm:, ... : see ?spd_builder for more info.   
            
    Returns:
        :returns: 
            | spds, M
            |   - 'spds': optimized spectrum.
            |   - 'M': ndarray with fluxes for each component spectrum.

    Notes:
        :Optimization algorithms:
            
        1. '2mixer':
        Pairs (odd,even) of components are selected and combined using 
        'pair_strength'. This process is continued until only 3 (combined)
        intermediate sources remain. Color3mixer is then used to calculate 
        the fluxes for the remaining 3 sources, after which the fluxes of 
        all components are back-calculated.
            
       2. '3mixer':
       The triangle/trio method creates for all possible combinations of 
       3 primary component spectra a spectrum that results in the target 
       chromaticity using color3mixer() and then optimizes the weights of
       each of the latter spectra such that adding them (additive mixing) 
       results in obj_vals as close as possible to the target values.

    """
            
    # Calculate Yxyt (target):
    Yxyt = colortf(target, tf = tar_type+'>Yxy', bwtf = cspace_bwtf)
    
    # Get component spd / data:
    if component_spds is None:
        if N_components is None: # Generate component spds from input args:
            if allow_butterworth_mono_spds == False:
                bw_order = -1
            spds = spd_builder(flux = None, peakwl = peakwl, fwhm = fwhm, \
                               bw_order = bw_order,\
                               strength_ph = strength_ph,\
                               peakwl_ph1 = peakwl_ph1, fwhm_ph1 = fwhm_ph1, strength_ph1 = strength_ph1,\
                               peakwl_ph2 = peakwl_ph2, fwhm_ph2 = fwhm_ph2, strength_ph2 = strength_ph2,\
                               verbosity = 0)
            N_components = spds.shape[0]
        else:
            spds = N_components # optimize spd model parameters, such as peakwl, fwhm, ... using N components.
                
    else:
        if isinstance(component_spds,dict): # optimize spectrum fluxes of set of component spectra defined by parameters in dict
            if N_components is None:
                N_components = component_spds['N_components']
        else: # optimize spectrum fluxes of pre-defined set of component spectra:
            spds = component_spds 
            N_components = spds.shape[0]
    
    # Check if there are at least 3 spds:
    if N_components < 3:
        raise Exception('spd_optimizer(): At least 3 component spds are required.')

    # optimize spectrum fluxes, model parameters, ... using optimizer_type method 
    spd_opt, M, component_spds, obj_vals, res = spd_optimizer_2_3(component_data = spds, wl = wl,\
                                                    allow_butterworth_mono_spds = allow_butterworth_mono_spds, \
                                                    optimizer_type = optimizer_type, 
                                                    spd_constructor = spd_constructor,\
                                                    spd_model_pars = spd_model_pars,\
                                                    Yxy_target = Yxyt, cieobs = cieobs,\
                                                    obj_fcn = obj_fcn, obj_fcn_pars = obj_fcn_pars, obj_fcn_weights = obj_fcn_weights,\
                                                    obj_tar_vals = obj_tar_vals, decimals = decimals, \
                                                    minimize_method = minimize_method, F_rss = F_rss,\
                                                    minimize_opts = minimize_opts,\
                                                    verbosity = verbosity)
    
    # store component spectra in spds with first axis components, second axis wavelengths
    spds = component_spds 
            
    # Calculate combined spd from components and their fluxes:
    spds = (np.atleast_2d(M)*spds[1:].T).T.sum(axis = 0)
    
    if with_wl == True:
        spds = np.vstack((getwlr(wl), spds))
    return spds, M       


#------------------------------------------------------------------------------
if __name__ == '__main__':
    
    plt.close('all')
    cieobs = '1931_2'
    
    #--------------------------------------------------------------------------
    print('1: spd_builder():')
    # Set up two basis LED spectra:
    target = 3500
    flux = [1,2,3]
#    peakwl = [450,530,590, 595, 600,620,630] # peak wavelengths of monochromatic leds
#    fwhm = [20,20,20,20,20,20,20] # fwhm of monochromatic leds
#    
#    peakwl = [450,530,590, 595] # peak wavelengths of monochromatic leds
#    fwhm = [20,20,20,20] # fwhm of monochromatic leds

    peakwl =[450,450,450]
    fwhm = [20,20,20]

    strength_ph = [0.3,0.6,0.3] # one monochromatic and one phosphor led
    
    # Parameters for phosphor 1:
    peakwl_ph1 = [530,550,550] 
    fwhm_ph1 = [80,80,80]
    strength_ph1 = [0.9,0.5,0.8]
    
    # Parameters for phosphor 1:
    peakwl_ph2 = [590,600,600]
    fwhm_ph2 = [90,90,90]
    strength_ph2 = None 
    
    # Build spd from parameters settings defined above:
    S = spd_builder(flux = flux, peakwl = peakwl, fwhm = fwhm,\
                    strength_ph = strength_ph,\
                    peakwl_ph1 = peakwl_ph1, fwhm_ph1 = fwhm_ph1, strength_ph1 = strength_ph1,\
                    peakwl_ph2 = peakwl_ph2, fwhm_ph2 = fwhm_ph2, strength_ph2 = strength_ph2,\
                    target = target, tar_type = 'cct', cieobs = cieobs,\
                    verbosity = 1)
    
    # Check output agrees with target:
    if target is not None:
        xyz = spd_to_xyz(S, relative = False, cieobs = cieobs)
        cct = xyz_to_cct(xyz, cieobs = cieobs, mode = 'lut')
        print("S: Phosphor model / target cct: {:1.1f} K / {:1.1f} K\n\n".format(cct[0,0], target))

        
    #plot final combined spd:
    plt.figure()
    SPD(S).plot(color = 'm')
    
    #--------------------------------------------------------------------------
    # Set up three basis LED spectra:
    flux = None
    peakwl = [450,530,610] # peak wavelengths of monochromatic leds
    fwhm = [30,35,15] # fwhm of monochromatic leds
    
    S2 = spd_builder(flux = flux,peakwl = peakwl, fwhm = fwhm,\
                    strength_ph = 0, verbosity = 1)
    
    #plot component spds:
    plt.figure()
    SPD(S2).plot()
 
    
    # Set peak wavelengths of monochromatic leds:
    peakwl = [450,470,610]
    
    # Set Full-Width-Half-Maxima of monochromatic leds:
    fwhm = [30,35,15] 
    
    bw_order = -1
    
    # Set phosphor strengths:
    strength_ph = [1.5, 0.4, 0]
    
    # Set phoshpor 1 parameters:
    strength_ph1 = [1, 1, 0]
    peakwl_ph1 = [530, 540, 1]
    fwhm_ph1 = [60, 60, 60]
    
    # Set phoshpor 2 parameters:
    strength_ph2 = [2, 1, 0]
    peakwl_ph2 = [590, 590, 590]
    fwhm_ph2 = [70, 70, 70]
    
    S = spd_builder(peakwl = peakwl, fwhm = fwhm, bw_order = bw_order,\
                            strength_ph = strength_ph, \
                            strength_ph1 = strength_ph1,\
                            peakwl_ph1 = peakwl_ph1,\
                            fwhm_ph1 = fwhm_ph1,\
                            strength_ph2 = strength_ph2,\
                            peakwl_ph2 = peakwl_ph2,\
                            fwhm_ph2 = fwhm_ph2,\
                           target = 3500, tar_type = 'cct',verbosity = 0)
    
    # Plot component spds:
    plt.figure()
    SPD(S).plot()
    
    # Check output agrees with target:
    S = S[(1*np.isnan(S)).sum(axis=1)==0,:] # get rid op nan spectra
    xyz = spd_to_xyz(S, relative = False, cieobs = cieobs)
    cct = xyz_to_cct(xyz, cieobs = cieobs, mode = 'lut')
    print(cct)
    
    #--------------------------------------------------------------------------
    print('2: spd_optimizer():')
    target = 4000 # 4000 K target cct
    tar_type = 'cct'
    peakwl = [450,530,560,610]
    fwhm = [30,35,30,15] 
    obj_fcn1 = cri.spd_to_iesrf
    obj_fcn2 = cri.spd_to_iesrg
    obj_fcn = [obj_fcn1, obj_fcn2]
    obj_tar_vals = [90,110]
    obj_fcn_weights = [1,1]
    decimals = [5,5]
    
    N_components = 5 #if not None, spd model parameters (peakwl, fwhm, ...) are optimized
    allow_butterworth_mono_spds = False
    S3, _ = spd_optimizer(target, tar_type = tar_type, cspace_bwtf = {'cieobs' : cieobs, 'mode' : 'search'},\
                          optimizer_type = '2mixer', N_components = N_components,\
                          allow_butterworth_mono_spds = allow_butterworth_mono_spds,\
                          peakwl = peakwl, fwhm = fwhm, obj_fcn = obj_fcn, obj_tar_vals = obj_tar_vals,\
                          obj_fcn_weights = obj_fcn_weights, decimals = decimals,\
                          use_piecewise_fcn=False, verbosity = 1)
    
    # Check output agrees with target:
    xyz = spd_to_xyz(S3, relative = False, cieobs = cieobs)
    cct = xyz_to_cct(xyz, cieobs = cieobs, mode = 'lut')
    Rf = obj_fcn1(S3)
    Rg = obj_fcn2(S3)
    print('\nS3: Optimization results:')
    print("S3: Optim / target cct: {:1.1f} K / {:1.1f} K".format(cct[0,0], target))
    print("S3: Optim / target Rf: {:1.3f} / {:1.3f}".format(Rf[0,0], obj_tar_vals[0]))
    print("S3: Optim / target Rg: {:1.3f} / {:1.3f}".format(Rg[0,0], obj_tar_vals[1]))
    
    #plot spd:
    plt.figure()
    SPD(S3).plot()
##    