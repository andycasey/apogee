pro ps2jpg,filename,rot=rot,eps=eps,chmod=chmod,delete=delete

; This program converts a postscript image to gif
; using the CONVERT function, and also allows for
; rotations.

if n_params(0) eq 0 then begin
  print,'Syntax - ps2jpg,filename,rot=rot,eps=eps'
  return
endif

files = file_search(filename)
if (files(0) eq '') then begin
  print,'FILE '+filename+' DOES NOT EXIST'
  return
endif
nfiles = n_elements(files)

; Multiple files to convert
if nfiles gt 1 then begin
  for i=0,nfiles-1 do ps2jpg,files(i),rot=rot,eps=eps
  return
end

; PS or EPS
if keyword_set(eps) then begin
  hi = strpos(filename,'.eps')
  gfile = strmid(filename,0,hi)+'.jpg'
endif else begin
  hi = strpos(filename,'.ps')
  gfile = strmid(filename,0,hi)+'.jpg'
endelse

if (hi(0) eq -1) then begin
  print,'FILE '+filename+' IS NOT A PS or EPS FILE'
  return
end

;f = strmid(file,0,hi)

; Does the file exist
if file_test(filename) eq 0 then begin
  print,filename,' NOT FOUND'
  return
endif

; Converting to JPG
;spawn,'convert '+filename+' '+gfile
file_delete,gfile,/allow_nonexistent
;spawn,['convert',filename,gfile],/noshell
spawn,['convert','-flatten',filename,gfile],/noshell
if keyword_set(chmod) then begin
  while ~file_test(gfile) do apwait,gfile,10
  file_chmod,gfile,chmod
endif
if keyword_set(delete) then file_delete,filename,/allow_nonexistent

; Rotating
;if (n_elements(rot) ne 0) then spawn,'mogrify -rotate '+strtrim(rot,2)+' '+gfile
if (n_elements(rot) ne 0) then spawn,['mogrify','-rotate',strtrim(rot,2),gfile],/noshell

;stop

end
