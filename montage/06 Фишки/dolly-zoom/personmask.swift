// Person mattes via Apple Vision: personmask <in_dir> <out_dir>
// Reads every *.png in in_dir, writes a same-size grayscale PNG mask (white = person) to out_dir.
import AppKit
import CoreImage
import Vision

let args = CommandLine.arguments
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let ctx = CIContext()
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".png") }.sorted()
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8

for f in files {
  let src = CIImage(contentsOf: inDir.appendingPathComponent(f))!
  try VNImageRequestHandler(ciImage: src).perform([req])
  let buf = req.results!.first!.pixelBuffer
  var m = CIImage(cvPixelBuffer: buf)
  m = m.transformed(by: CGAffineTransform(scaleX: src.extent.width / m.extent.width, y: src.extent.height / m.extent.height))
  let cg = ctx.createCGImage(m, from: src.extent, format: .L8, colorSpace: CGColorSpaceCreateDeviceGray())!
  let rep = NSBitmapImageRep(cgImage: cg)
  try rep.representation(using: .png, properties: [:])!.write(to: outDir.appendingPathComponent(f))
}
print("masks: \(files.count)")
