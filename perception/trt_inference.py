import os
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import numpy as np

class TRTInference:
    def __init__(self, engine_path):
        """
        初始化 TensorRT 推論引擎
        :param engine_path: .engine 檔案路徑
        """
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.runtime = trt.Runtime(self.logger)
        
        if not os.path.exists(engine_path):
            raise FileNotFoundError(f"TensorRT Engine not found at {engine_path}")
            
        with open(engine_path, "rb") as f:
            self.engine = self.runtime.deserialize_cuda_engine(f.read())
            
        self.context = self.engine.create_execution_context()
        self.stream = cuda.Stream()
        
        # 分配 Host/Device 記憶體
        self.inputs = []
        self.outputs = []
        self.bindings = []
        
        for binding in self.engine:
            size = trt.volume(self.engine.get_binding_shape(binding))
            dtype = trt.nptype(self.engine.get_binding_dtype(binding))
            
            # 分配 Page-locked host memory
            host_mem = cuda.pagelocked_empty(size, dtype)
            # 分配 Device memory
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if self.engine.binding_is_input(binding):
                self.inputs.append({"host": host_mem, "device": device_mem})
            else:
                self.outputs.append({"host": host_mem, "device": device_mem})

    def run(self, input_data):
        """
        執行非同步推論
        :param input_data: numpy array
        :return: 推論結果列表
        """
        # 1. 拷貝輸入至 Host 記憶體
        np.copyto(self.inputs[0]["host"], input_data.ravel())
        
        # 2. 傳輸至 Device (H2D)
        cuda.memcpy_htod_async(self.inputs[0]["device"], self.inputs[0]["host"], self.stream)
        
        # 3. 執行推論
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        # 4. 傳輸結果至 Host (D2H)
        for out in self.outputs:
            cuda.memcpy_dtoh_async(out["host"], out["device"], self.stream)
            
        # 5. 等待同步
        self.stream.synchronize()
        
        return [out["host"] for out in self.outputs]

    def __del__(self):
        # 釋放資源
        pass
