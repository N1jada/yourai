"use client";

/**
 * DocumentUpload — Drag-and-drop + file picker for uploading documents.
 */

import { useState, useRef, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/auth-context";
import { Upload, FileUp, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
];
const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

interface DocumentUploadProps {
  knowledgeBaseId: string;
}

export function DocumentUpload({ knowledgeBaseId }: DocumentUploadProps) {
  const { api } = useAuth();
  const queryClient = useQueryClient();

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.documents.upload(knowledgeBaseId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", knowledgeBaseId],
      });
    },
  });

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.endsWith(".txt")) {
      return `Unsupported format: ${file.name}. Use PDF, DOCX, or TXT.`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File too large: ${file.name} (max 50MB).`;
    }
    return null;
  };

  const handleFiles = useCallback((files: FileList | File[]) => {
    setError(null);
    const validFiles: File[] = [];

    for (const file of Array.from(files)) {
      const err = validateFile(file);
      if (err) {
        setError(err);
        return;
      }
      validFiles.push(file);
    }

    setSelectedFiles(validFiles);
  }, []);

  const handleUpload = async () => {
    for (const file of selectedFiles) {
      await uploadMutation.mutateAsync(file);
    }
    setSelectedFiles([]);
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          isDragging
            ? "border-blue-400 bg-blue-50"
            : "border-neutral-300 hover:border-neutral-400 hover:bg-neutral-50",
        )}
        role="button"
        aria-label="Upload documents"
      >
        <Upload className="h-8 w-8 text-neutral-400" />
        <p className="text-sm text-neutral-600">
          Drag and drop files here, or click to browse
        </p>
        <p className="text-xs text-neutral-400">PDF, DOCX, or TXT (max 50MB)</p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        multiple
        onChange={(e) => {
          if (e.target.files) handleFiles(e.target.files);
        }}
        className="hidden"
      />

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      {/* Selected files */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          {selectedFiles.map((file, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-md border border-neutral-200 px-3 py-2"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileUp className="h-4 w-4 text-neutral-500" />
                <span className="truncate text-sm">{file.name}</span>
                <span className="text-xs text-neutral-400">
                  ({(file.size / 1024 / 1024).toFixed(1)} MB)
                </span>
              </div>
              <button
                onClick={() =>
                  setSelectedFiles((prev) => prev.filter((_, j) => j !== i))
                }
                className="text-neutral-400 hover:text-neutral-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}

          <Button
            onClick={handleUpload}
            disabled={uploadMutation.isPending}
            className="w-full"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""}
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
