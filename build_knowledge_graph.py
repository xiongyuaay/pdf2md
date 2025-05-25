#!/usr/bin/env python3
"""
知识图谱构建命令行工具
"""

import os
import sys
import argparse
from knowledge_graph.knowledge_graph_builder import KnowledgeGraphBuilder


def main():
    parser = argparse.ArgumentParser(description='构建基于Sentence Transformers的知识图谱')
    
    parser.add_argument('--embedding_model', '-e', type=str, default='paraphrase-multilingual-MiniLM-L12-v2', 
                        help='Sentence Transformers嵌入模型名称 (默认: paraphrase-multilingual-MiniLM-L12-v2)')
    parser.add_argument('--threshold', '-t', type=float, default=0.7, help='相似度阈值 (默认: 0.7)')
    parser.add_argument('--max_relations', '-m', type=int, default=5, help='每个知识点最多关联数量 (默认: 5)')
    
    args = parser.parse_args()
    args.input = r"E:/pdf教材知识整理/pdf2md/output/数学问题v1.0-_knowledge_points.json"
    args.output = r"E:/pdf教材知识整理/pdf2md/output/数学问题v1.0-_graph.json"
    
    builder = KnowledgeGraphBuilder(
        embedding_model_name=args.embedding_model
    )
    
    print("处理中...")
    output_path = builder.process_knowledge_file(
        args.input,
        args.output,
        similarity_threshold=args.threshold,
        max_relations=args.max_relations
    )
    
    print("处理完成")


if __name__ == "__main__":
    main() 