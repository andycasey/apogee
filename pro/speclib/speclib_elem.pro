function speclib_elem,n,abun=abun

elem=['H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar','K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr','Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I','Xe','Cs','Ba','La','Ce','Pr','Nd']

elem=['H ','He','Li','Be','B ','C ','N ','O ','F ',$          ;  1 -  9
      'Ne','Na','Mg','Al','Si','P ','S ','Cl','Ar',$          ; 10 - 18
      'K ','Ca','Sc','Ti','V ','Cr','Mn','Fe','Co',$          ; 19 - 27
      'Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr',$          ; 28 - 36
      'Rb','Sr','Y ','Zr','Nb','Mo','Tc','Ru','Rh',$          ; 37 - 45
      'Pd','Ag','Cd','In','Sn','Sb','Te','I ','Xe',$          ; 46 - 54
      'Cs','Ba','La','Ce','Pr','Nd','Pm','Sm','Eu',$          ; 55 - 63
      'Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu','Hf',$          ; 64 - 72
      'Ta','W ','Re','Os','Ir','Pt','Au','Hg','Tl',$          ; 73 - 81
      'Pb','Bi','Po','At','Rn','Fr','Ra','Ac','Th',$          ; 82 - 90
      'Pa','U ']                                             ; 91 - 92

elemabun= [ 12.00, 10.93,  1.05,  1.38,  2.70,  8.39,  7.78,  8.66,  4.56,$   ;  1 -  9
              7.84,  6.17,  7.53,  6.37,  7.51,  5.36,  7.14,  5.50,  6.18,$   ; 10 - 18
              5.08,  6.31,  3.17,  4.90,  4.00,  5.64,  5.39,  7.45,  4.92,$   ; 19 - 27
              6.23,  4.21,  4.60,  2.88,  3.58,  2.29,  3.33,  2.56,  3.25,$   ; 28 - 36
              2.60,  2.92,  2.21,  2.58,  1.42,  1.92, -99.0,  1.84,  1.12,$   ; 37 - 45
              1.66,  0.94,  1.77,  1.60,  2.00,  1.00,  2.19,  1.51,  2.24,$   ; 46 - 54
              1.07,  2.17,  1.13,  1.70,  0.58,  1.45, -99.0,  1.00,  0.52,$   ; 55 - 63
              1.11,  0.28,  1.14,  0.51,  0.93,  0.00,  1.08,  0.06,  0.88,$   ; 64 - 72
             -0.17,  1.11,  0.23,  1.25,  1.38,  1.64,  1.01,  1.13,  0.90,$   ; 73 - 81
              2.00,  0.65, -99.0, -99.0, -99.0, -99.0, -99.0, -99.0,  0.06,$   ; 82 - 90
             -99.0, -0.52 ]                                                   ; 91 - 92


if size(n,/type) eq 7 then begin
  j=where(elem eq n)
  abun=elemabun[j[0]]
  return,j+1
endif else begin
  abun=elemabun[n-1]
  if n eq 0 then return,'' else return,elem[n-1]
endelse

end