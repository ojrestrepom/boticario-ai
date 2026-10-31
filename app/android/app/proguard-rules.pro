# ONNX Runtime JNI resolves these classes and members by their original names.
# Required by flutter_onnxruntime for R8-minimized release builds.
-keep class ai.onnxruntime.** { *; }
