ObjC.import('Quartz'); ObjC.import('Foundation');
function run(argv){
  var url=$.NSURL.fileURLWithPath($(argv[0]));
  var doc=$.PDFDocument.alloc.initWithURL(url);
  var n=doc.pageCount; var out=[];
  for(var i=0;i<n;i++){ var p=doc.pageAtIndex(i); out.push('\n===== PAGE '+(i+1)+' =====\n'+ObjC.unwrap(p.string)); }
  $(out.join('\n')).writeToFileAtomicallyEncodingError($(argv[1]),true,$.NSUTF8StringEncoding,null);
  return 'pages='+n;
}
