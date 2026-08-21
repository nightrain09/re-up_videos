import os
import math

class FileProcessor:
    @staticmethod
    def SplitFile(FilePath, MaxSizeMB=20):
        MaxSizeBytes = MaxSizeMB * 1024 * 1024
        FileSize = os.path.getsize(FilePath)
        if FileSize <= MaxSizeBytes:
            return [FilePath]

        Chunks = []
        NumChunks = math.ceil(FileSize / MaxSizeBytes)
        with open(FilePath, 'rb') as f:
            for i in range(NumChunks):
                ChunkName = f"{FilePath}.Part{i}"
                Data = f.read(MaxSizeBytes)
                with open(ChunkName, 'wb') as cf:
                    cf.write(Data)
                Chunks.append(ChunkName)
        return Chunks

    @staticmethod
    def MergeResults(ChunkList, OutputPath):
        with open(OutputPath, 'w', encoding='utf-8') as f:
            for Chunk in ChunkList:
                if os.path.exists(Chunk):
                    with open(Chunk, 'r', encoding='utf-8') as cf:
                        f.write(cf.read())
                    if ".Part" in Chunk:
                        os.remove(Chunk)
