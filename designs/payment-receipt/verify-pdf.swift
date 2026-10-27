import AppKit
import PDFKit
let root=CommandLine.arguments[1]
let doc=PDFDocument(url:URL(fileURLWithPath:root+"/receipt.pdf"))!
guard doc.pageCount == 1, let page=doc.page(at:0) else { fatalError("Receipt must be exactly one page") }
let box=page.bounds(for:.mediaBox)
guard abs(box.width-595.28)<1 && abs(box.height-841.89)<1 else { fatalError("Not A4") }
let text=doc.string ?? ""
for expected in ["₹49.00", "REO-RCP-2627-000001", "REO-ORD-2627-000001", "SAMPLE-CAPTURE-000001", "No GST has been charged or collected.", "18:00 IST", "SAMPLE"] { guard text.contains(expected) else {fatalError("Missing PDF text: \(expected)")} }
guard !text.contains("�") else { fatalError("Broken characters") }
let image=page.thumbnail(of:NSSize(width:1191,height:1684),for:.mediaBox)
let rep=NSBitmapImageRep(data:image.tiffRepresentation!)!
try rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:root+"/receipt-preview.png"))
try text.write(toFile:root+"/pdf-extracted.txt",atomically:true,encoding:.utf8)
let evidence:[String:Any]=["pageCount":doc.pageCount,"widthPoints":box.width,"heightPoints":box.height,"textChecks":"passed; rupee glyph and required references present","previewSource":"PDFKit rasterization of final Chromium PDF"]
try JSONSerialization.data(withJSONObject:evidence,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:root+"/pdf-verification.json"))
print(String(data:try JSONSerialization.data(withJSONObject:evidence,options:[.prettyPrinted]),encoding:.utf8)!)
