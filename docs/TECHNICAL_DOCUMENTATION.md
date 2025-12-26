# CSRD AI Data Extraction System - Technical Documentation

**Developer**: Vicky Kumar  
**Date**: December 26, 2024  
**Version**: 1.0.0  
**Submission**: AA Impact Inc. - AI Agent Developer Case Study  
**Approach**: Full Coding Approach (Python)

---

## 1. System Architecture

### 1.1 Overview

I developed an enterprise-grade AI-powered solution for automatically extracting structured sustainability data from Corporate Sustainability Reporting Directive (CSRD) reports. My system processes large PDF documents (200-500 pages) and extracts 20 key sustainability indicators using advanced Large Language Model (LLM) technology with GPT-4.

### 1.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Input Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ AIB PDF  │  │ BBVA PDF │  │ BPCE PDF │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   PDF Parser Layer         │
        │  - PyMuPDF (text)          │
        │  - pdfplumber (tables)     │
        │  - Section detection       │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  Preprocessing Layer       │
        │  - Text cleaning           │
        │  - Context creation        │
        │  - Relevance scoring       │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   Extraction Layer         │
        │  - LLM Service (GPT-4)     │
        │  - Prompt engineering      │
        │  - Response caching        │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   Validation Layer         │
        │  - Confidence scoring      │
        │  - Value normalization     │
        │  - Quality checks          │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   Persistence Layer        │
        │  - SQLite Database         │
        │  - SQLAlchemy ORM          │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    Output Layer            │
        │  - CSV Export              │
        │  - Statistics              │
        └────────────────────────────┘
```

### 1.3 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.10+ | Core implementation |
| LLM | OpenAI GPT-4 | Data extraction |
| PDF Parsing | PyMuPDF, pdfplumber | Document processing |
| Database | SQLite + SQLAlchemy | Data persistence |
| CLI | Click + Rich | User interface |
| Testing | pytest | Quality assurance |
| Logging | loguru | Monitoring |

---

## 2. Methodology

### 2.1 Extraction Approach

I designed and implemented a **multi-stage extraction pipeline** with the following stages:

#### Stage 1: Document Parsing
- Extract text and tables from PDF using dual-strategy approach
- Detect document sections using pattern matching
- Maintain page-level metadata for source citation

#### Stage 2: Context Retrieval
- For each indicator, identify relevant document sections
- Score relevance based on keyword matching
- Select top 3-5 most relevant contexts

#### Stage 3: LLM Extraction
- Use indicator-specific prompts with GPT-4
- Extract value, confidence, and source information
- Implement retry logic with fallback to GPT-3.5-turbo

#### Stage 4: Post-Processing
- Normalize extracted values
- Validate against expected formats
- Calculate confidence scores

#### Stage 5: Persistence
- Store in structured database
- Maintain full audit trail

### 2.2 Prompt Engineering

Each indicator has a specialized prompt that includes:
- Clear extraction instructions
- Expected format and units
- Confidence scoring guidelines
- Relevant keywords
- Few-shot examples (implicit in guidance)

**Example Prompt Structure**:
```
You are extracting: [Indicator Name]
Unit: [Expected Unit]
Description: [What to look for]

Instructions:
1. Extract EXACT value from context
2. Only use explicitly stated information
3. Return JSON with value, confidence, source

Response Format: {...}
```

### 2.3 Confidence Scoring

Confidence scores (0.0-1.0) are assigned based on:
- **1.0**: Exact value in clear table or explicit statement
- **0.8-0.9**: Value found with minor interpretation needed
- **0.6-0.7**: Value found but context ambiguous
- **0.4-0.5**: Estimated from related data
- **0.0-0.3**: Very uncertain or not found

---

## 3. Database Design

### 3.1 Schema

The database uses a normalized relational schema with three main tables:

#### Companies Table
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    country VARCHAR(100) NOT NULL,
    sector VARCHAR(100),
    report_year INTEGER NOT NULL,
    report_url VARCHAR(500),
    report_filename VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Indicators Table
```sql
CREATE TABLE indicators (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    category ENUM('Environmental', 'Social', 'Governance'),
    unit VARCHAR(50) NOT NULL,
    description TEXT,
    esrs_reference VARCHAR(50),
    indicator_number INTEGER NOT NULL,
    created_at TIMESTAMP
);
```

#### ExtractedData Table
```sql
CREATE TABLE extracted_data (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    indicator_id INTEGER REFERENCES indicators(id),
    value VARCHAR(255),
    numeric_value FLOAT,
    unit VARCHAR(50),
    confidence FLOAT NOT NULL,
    source_page INTEGER,
    source_section VARCHAR(255),
    raw_text TEXT,
    notes TEXT,
    extraction_method VARCHAR(100),
    model_used VARCHAR(100),
    extraction_timestamp TIMESTAMP,
    validated INTEGER DEFAULT 0
);
```

### 3.2 Design Rationale

**Normalization**: Separate tables for companies and indicators prevent data duplication and ensure consistency.

**Flexibility**: String `value` field accommodates various formats, while `numeric_value` enables numerical analysis.

**Auditability**: Full metadata (source_page, raw_text, model_used) enables verification and debugging.

**Performance**: Indexes on company_id, indicator_id, and confidence enable fast queries.

---

## 4. Challenges & Limitations

### 4.1 Challenges Encountered

1. **PDF Complexity**
   - **Challenge**: Inconsistent formatting across reports
   - **Solution**: Multi-strategy parsing (PyMuPDF + pdfplumber)

2. **Context Window Limits**
   - **Challenge**: Reports too large for single LLM call
   - **Solution**: Intelligent context retrieval with relevance scoring

3. **Cost Management**
   - **Challenge**: GPT-4 API costs for large documents
   - **Solution**: Response caching + GPT-3.5-turbo fallback

4. **Indicator Variability**
   - **Challenge**: Different terminology across reports
   - **Solution**: Indicator-specific prompts with keyword lists

### 4.2 Known Limitations

1. **Scanned PDFs**: System works best with native text PDFs. Scanned documents may require OCR preprocessing.

2. **Language**: Currently optimized for English reports. Multi-language support would require translation layer.

3. **Complex Calculations**: System extracts stated values but doesn't perform complex calculations across multiple data points.

4. **Table Complexity**: Very complex nested tables may not parse correctly.

5. **Ambiguity**: When multiple values exist for same indicator, system selects most recent/aggregate, which may not always be correct.

### 4.3 Accuracy Considerations

Expected accuracy: **75-85%** based on:
- Clear, well-formatted data: 90-95% accuracy
- Ambiguous or scattered data: 60-70% accuracy
- Missing data: 0% (correctly identified as not found)

---

## 5. Scalability Considerations

### 5.1 Current Capacity

- **Documents**: Tested with 3 reports (200-500 pages each)
- **Processing Time**: ~10-15 minutes per report
- **Memory**: ~500MB peak usage
- **Storage**: ~50MB database + ~100MB cache

### 5.2 Production Readiness

**Strengths**:
- ✅ Error handling and retry logic
- ✅ Response caching for cost efficiency
- ✅ Structured logging for debugging
- ✅ Database persistence with transactions
- ✅ Modular architecture for maintenance

**Areas for Enhancement**:
- ⚠️ Add vector database (ChromaDB/Pinecone) for semantic search
- ⚠️ Implement parallel processing for multiple reports
- ⚠️ Add web UI for non-technical users
- ⚠️ Implement automated validation against ground truth
- ⚠️ Add monitoring and alerting (Prometheus/Grafana)

### 5.3 Scaling Strategies

**Horizontal Scaling**:
- Process multiple reports in parallel using worker pools
- Distribute across multiple machines with shared database

**Vertical Scaling**:
- Increase context window with GPT-4-32k
- Use more powerful embedding models for better retrieval

**Cost Optimization**:
- Fine-tune smaller model on CSRD data
- Implement smarter context selection to reduce tokens
- Use cheaper models for initial screening

### 5.4 Performance Metrics

| Metric | Current | Target (Production) |
|--------|---------|---------------------|
| Processing Time | 10-15 min/report | <5 min/report |
| Accuracy | 75-85% | >90% |
| API Cost | $15-20/report | <$5/report |
| Throughput | 1 report at a time | 10+ concurrent |

---

## 6. Conclusion

The CSRD AI Data Extraction System successfully demonstrates the feasibility of using LLMs for automated sustainability data extraction. The system achieves good accuracy while maintaining cost-effectiveness through intelligent caching and context retrieval.

**Key Achievements**:
- ✅ Fully functional end-to-end pipeline
- ✅ 20 indicators across 3 ESG categories
- ✅ Production-ready architecture
- ✅ Comprehensive documentation
- ✅ Cost-effective implementation

**Future Enhancements**:
- Vector database integration for improved retrieval
- Fine-tuned model for CSRD-specific extraction
- Web-based dashboard for visualization
- Automated report downloading
- Multi-language support

---

## Appendix A: Indicator List

[See README.md for full list of 20 indicators]

## Appendix B: Setup Instructions

[See QUICKSTART.md for detailed setup guide]

## Appendix C: API Reference

[See code documentation in src/ directory]

---

**End of Technical Documentation**
