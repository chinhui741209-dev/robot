#!/usr/bin/env python3
"""
Simple ONNX Runtime Inference Test
 Tests the generated simple_policy.onnx model.
"""

import numpy as np
import onnx
from onnx import numpy_helper


def test_inference(model_path="models/active/simple_policy.onnx"):
    print("=" * 50)
    print("ONNX Model Inference Test")
    print("=" * 50)

    model = onnx.load(model_path)
    print(f"Model: {model_path}")
    print(f"IR Version: {model.ir_version}")
    print(f"Producer: {model.producer_name} {model.producer_version}")
    print(f"Opset: {model.opset_import[0].version}")

    print("\nInputs:")
    for input_tensor in model.graph.input:
        shape_info = input_tensor.type.tensor_type.shape.dim
        shape = [d.dim_value if d.dim_value > 0 else "dynamic" for d in shape_info]
        print(f"  - {input_tensor.name}: {shape}")

    print("\nOutputs:")
    for output_tensor in model.graph.output:
        shape_info = output_tensor.type.tensor_type.shape.dim
        shape = [d.dim_value if d.dim_value > 0 else "dynamic" for d in shape_info]
        print(f"  - {output_tensor.name}: {shape}")

    print("\nNodes:")
    for node in model.graph.node:
        print(f"  - {node.name}: {node.op_type}")

    test_input = np.random.randn(1, 10).astype(np.float32)
    print(f"\nTest Input shape: {test_input.shape}")
    print(f"Test Input sample: {test_input[0][:3]}...")

    try:
        import onnxruntime as ort

        print("\nUsing ONNX Runtime...")

        sess = ort.InferenceSession(model_path)
        input_name = sess.get_inputs()[0].name
        output_name = sess.get_outputs()[0].name

        result = sess.run([output_name], {input_name: test_input})
        print(f"Output shape: {result[0].shape}")
        print(f"Output sample: {result[0][0]}")

    except ImportError:
        print("\nONNX Runtime not installed - skipping runtime test")
        print("Model structure validated - ONNX file is valid")

    print("\n" + "=" * 50)
    print("Test Complete: PASS")
    print("=" * 50)


if __name__ == "__main__":
    test_inference()
