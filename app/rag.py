"""
Modul RAG — mengubah knowledge base menjadi embedding, menyimpannya ke FAISS,
melakukan semantic search, lalu menghasilkan jawaban menggunakan LLM.

Alur ini serupa dengan yang sudah dibangun di Assignment 3 (Semantic Search &
LLM Application) dan Sesi 11 (Building a Simple RAG System) — di assignment ini,
alur tersebut dibungkus menjadi fungsi yang dipanggil oleh router.py.
"""

import os
from numpy.strings import index
import pandas as pd
import numpy as np
import faiss
from google import genai  # sesuaikan dengan library Gemini API yang digunakan
from dotenv import load_dotenv

load_dotenv()
_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

KNOWLEDGE_BASE_PATH = "data/it_helpdesk_knowledge_base.csv"

# 🔧 TODO: muat knowledge base dan bangun index FAISS saat aplikasi startup
# (bukan di setiap request), agar lebih efisien. Pertimbangkan menggunakan
# FastAPI startup event atau lazy-loading dengan cache sederhana.

_index = None
_documents = None
_df = None
MODEL = "gemini-3.1-flash-lite"
MODEL_EMBEDDING = "gemini-embedding-001"  # sesuaikan versi model embedding


def _get_embedding(text: str):
    result = _client.models.embed_content(
        model=MODEL_EMBEDDING,  # sesuaikan versi model embedding
        contents=text,
    )
    return result.embeddings[0].values


def build_index():
    """
    # TODO: implementasikan pembangunan index FAISS dari knowledge base CSV.
    # Referensi: starter_notebook_semantic_search.ipynb dari Assignment 3,
    # Section 1-4 (load data -> unit retrievable -> embedding -> simpan ke FAISS).
    """

    global _index, _documents, _df

    if _index is not None:
        return

    _df = pd.read_csv(KNOWLEDGE_BASE_PATH)

    # 2. Membentuk unit retrievable
    _documents = [
        f"Pertanyaan: {row['question']}\nJawaban: {row['answer']}"
        for _, row in _df.iterrows()
    ]

    # 3. Membuat embeddings untuk seluruh dokumen
    embeddings = np.array(
        [_get_embedding(doc) for doc in _documents],
        dtype=np.float32
    )

    # 4. Membuat FAISS index (sama seperti Assignment 3)
    dimension = embeddings.shape[1]
    _index = faiss.IndexFlatL2(dimension)

    # 5. Memasukkan embeddings ke FAISS
    _index.add(embeddings)

    print("Jumlah vektor tersimpan di index:", _index.ntotal)

    return
    # raise NotImplementedError("Implementasikan build_index di sini")


def semantic_search(query: str, top_k: int = 3):
    """
    # TODO: implementasikan semantic search terhadap index yang sudah dibangun.
    # Referensi: starter_notebook_semantic_search.ipynb, Section 5.
    """

    if _index is None:
        build_index()

    # Mengubah query menjadi embedding
    query_embedding = np.array([_get_embedding(query)]).astype('float32')

    # Membatasi top_k agar tidak melebihi jumlah dokumen yang ada   
    top_k = min(top_k, _index.ntotal)
    
    # Mencari vektor terdekat
    distances, indices = _index.search(query_embedding, top_k)

    results = []
    for rank, idx in enumerate(indices[0]):
        results.append({
            'rank': rank + 1,
            'question': _df.iloc[idx]['question'],
            'answer': _df.iloc[idx]['answer'],
            'category': _df.iloc[idx]['category'],
            'distance': distances[0][rank]
        })
    return results

    raise NotImplementedError("Implementasikan semantic_search di sini")


async def answer_from_knowledge_base(query: str) -> str:
    """
    Fungsi yang dipanggil router.py ketika intent = 'faq'.
    Menjalankan semantic search, menyusun prompt dengan context hasil retrieval,
    lalu memanggil LLM untuk menghasilkan jawaban.

    # TODO: implementasikan alur lengkap: semantic_search -> build prompt
    # (Persona/Task/Context/Format, lihat Assignment 3 Section 6) -> panggil LLM.
    """

    # mengambil FAQ relevan dari knowledge base menggunakan semantic search
    search_results = semantic_search(query, top_k=3)

    # Menyusun context berdasarkan hasil retrieval
    context = '\n\n'.join(
        f"FAQ: {r['question']}\nJawaban: {r['answer']}"
        for r in search_results
    )

    #  Menyusun prompt (Persona, Task, Context, Format)
    prompt = f"""
        Persona:
        Kamu adalah AI Helpdesk Assistant internal perusahaan
        yang ramah, profesional, dan membantu karyawan.

        
        Tugas:
        Jawab pertanyaan pengguna HANYA berdasarkan informasi FAQ
        dari knowledge base yang diberikan.
        Jika informasi tidak ditemukan dalam FAQ, 
        katakan bahwa kamu belum memiliki informasi tersebut 
        dan sarankan menghubungi tim People & IT Operations.

        Konteks FAQ relevan:
        {context}

        Pertanyaan pengguna:
        {query}

        Format:
        Berikan jawaban dalam bahasa Indonesia yang jelas,
        singkat, sopan, dan mudah dipahami.
    """

    # Memanggil LLM untuk menghasilkan jawaban
    response = await _client.aio.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    if not response.text:
        raise RuntimeError("LLM tidak menghasilkan jawaban.")

    return response.text

    # raise NotImplementedError("Implementasikan answer_from_knowledge_base di sini")
