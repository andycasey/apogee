function create_index,arr,index

; Create an index of array values like reverse indices.
if n_elements(arr) eq 0 then begin
  print,'Syntax - index = create_index(arr)'
  return,-1
endif

si = sort(arr)
sarr = arr[si]
brklo = where(sarr ne shift(sarr,1),nbrk)
brkhi = [brklo[1:nbrk-1]-1,n_elements(arr)-1]
num = brkhi-brklo+1
index = {index:si,value:sarr[brklo],num:num,lo:brklo,hi:brkhi}
return,index

end
