"""Tiny synthetic ONNX graphs that mimic real swap-model signatures.

They contain no trained weights and produce meaningless pixels — they exist to
prove the engine's graph introspection, latent caching and paste-back plumbing.
"""

from __future__ import annotations

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper


def _const(name: str, array: np.ndarray):
    return numpy_helper.from_array(array.astype(np.float32), name)


def latent_swapper(path, size: int = 128) -> str:
    """inswapper-style: image input + 512-d source latent, two outputs."""
    inp = helper.make_tensor_value_info("target", TensorProto.FLOAT, [1, 3, size, size])
    latent = helper.make_tensor_value_info("source", TensorProto.FLOAT, [1, 512])
    out = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, size, size])
    emap = helper.make_tensor_value_info("emap", TensorProto.FLOAT, [1, 512])
    weight = np.zeros((3, 512), dtype=np.float32)
    for i in range(3):
        weight[i, i * 7] = 1.0
    nodes = [
        helper.make_node("GlobalAveragePool", ["target"], ["gap"]),
        helper.make_node("Flatten", ["gap"], ["flat"], axis=1),
        helper.make_node("MatMul", ["flat", "W"], ["emap"]),
        helper.make_node("Mul", ["target", "half"], ["output"]),
    ]
    graph = helper.make_graph(
        nodes, "latent_swapper",
        [inp, latent], [out, emap],
        initializer=[_const("W", weight), _const("half", np.array(0.5))],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=8)
    onnx.save(model, str(path))
    return str(path)


def dual_image_swapper(path, size: int = 128) -> str:
    inp_s = helper.make_tensor_value_info("source", TensorProto.FLOAT, [1, 3, size, size])
    inp_t = helper.make_tensor_value_info("target", TensorProto.FLOAT, [1, 3, size, size])
    out = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, size, size])
    nodes = [
        helper.make_node("Mul", ["target", "half"], ["t2"]),
        helper.make_node("Mul", ["source", "quarter"], ["s2"]),
        helper.make_node("Add", ["t2", "s2"], ["output"]),
    ]
    graph = helper.make_graph(nodes, "dual_swap", [inp_s, inp_t], [out],
                              initializer=[_const("half", np.array(0.5)),
                                           _const("quarter", np.array(0.25))])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=8)
    onnx.save(model, str(path))
    return str(path)


def not_a_swapper(path) -> str:
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 3])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 3])
    graph = helper.make_graph([helper.make_node("Identity", ["x"], ["y"])], "tiny", [x], [y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=8)
    onnx.save(model, str(path))
    return str(path)
