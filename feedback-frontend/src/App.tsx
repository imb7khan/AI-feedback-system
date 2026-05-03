import React, { useState } from 'react';
import './App.css';

interface ParagraphFeedback {
  paragraph_index: number;
  text: string;
  overall_feedback: string;
  rubric_scores: Record<string, string>;
  total_score: number;
  max_score: number;
  strengths: string[];
  improvements: string[];
}

interface RubricScores {
  total_points: number;
  max_points: number;
  percentage: number;
  letter_grade: string;
}

interface OverallFeedback {
  summary: string;
  key_strengths: string[];
  key_improvements: string[];
}

interface PlagiarismFlag {
  type: string;
  paragraph_indices: number[];
  evidence: string;
  confidence: number;
}

interface PlagiarismAnalysis {
  risk_level: string;
  flags: PlagiarismFlag[];
  note: string;
}

interface PipelineResponse {
  success: boolean;
  pipeline_status: {
    step: string;
    status: string;
    message: string;
  };
  processing_info?: {
    file_name: string;
    file_type: string;
    text_length: number;
    paragraph_count: number;
    model_used: string;
  };
  paragraph_feedback?: ParagraphFeedback[];
  rubric_scores?: RubricScores;
  overall_feedback?: OverallFeedback;
  suggestions?: string[];
  plagiarism_analysis?: PlagiarismAnalysis | null;
  error?: string;
}

function App() {
  const defaultModel = 'llama-3.1-8b-instant';
  const [file, setFile] = useState<File | null>(null);
  const [assignmentType, setAssignmentType] = useState('essay');
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResponse(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('assignment_type', assignmentType);
      if (context) {
        formData.append('context', context);
      }
      // Use a low-cost default model to reduce rate-limit failures in local testing.
      formData.append('model', defaultModel);
      formData.append('save_submission', 'false');

      const response = await fetch('http://127.0.0.1:8000/api/complete-pipeline/', {
        method: 'POST',
        body: formData,
      });

      const data: PipelineResponse = await response.json();
      setResponse(data);

      if (!data.success) {
        setError(data.error || 'Processing failed');
      }
    } catch (err) {
      setError('Failed to connect to the server. Please make sure the backend is running.');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getGradeColor = (grade: string): string => {
    const colors: Record<string, string> = {
      'A': 'bg-green-500',
      'B': 'bg-blue-500',
      'C': 'bg-yellow-500',
      'D': 'bg-orange-500',
      'F': 'bg-red-500',
    };
    return colors[grade] || 'bg-gray-500';
  };

  const getPlagiarismRiskStyles = (risk: string): { badge: string; panel: string } => {
    switch (risk) {
      case 'high':
        return { badge: 'bg-red-600 text-white', panel: 'border-red-200 bg-red-50' };
      case 'medium':
        return { badge: 'bg-amber-500 text-white', panel: 'border-amber-200 bg-amber-50' };
      default:
        return { badge: 'bg-emerald-600 text-white', panel: 'border-emerald-200 bg-emerald-50' };
    }
  };

  const formatParagraphRefs = (indices: number[]): string =>
    indices.map((i) => i + 1).join(', ');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            AI Assignment Feedback System
          </h1>
          <p className="text-gray-600">
            Upload your essay and get instant AI-powered feedback
          </p>
        </div>

        {/* Upload Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload Essay (PDF, DOCX, or TXT)
              </label>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {file && (
                <p className="mt-2 text-sm text-green-600">
                  Selected: {file.name}
                </p>
              )}
            </div>

            {/* Assignment Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Assignment Type
              </label>
              <select
                value={assignmentType}
                onChange={(e) => setAssignmentType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="essay">Essay</option>
                <option value="research_paper">Research Paper</option>
                <option value="report">Report</option>
                <option value="article">Article</option>
              </select>
            </div>

            {/* Context (Optional) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Context (Optional)
              </label>
              <textarea
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Additional context about the assignment..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !file}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : 'Get Feedback'}
            </button>
          </form>

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800">{error}</p>
            </div>
          )}
        </div>

        {/* Results Display */}
        {response && response.success && (
          <div className="space-y-6">
            {/* Overall Score */}
            {response.rubric_scores && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Overall Score
                </h2>
                <div className="flex items-center justify-center">
                  <div className={`text-6xl font-bold text-white ${getGradeColor(response.rubric_scores.letter_grade)} rounded-full w-32 h-32 flex items-center justify-center`}>
                    {response.rubric_scores.letter_grade}
                  </div>
                </div>
                <div className="text-center mt-4">
                  <p className="text-2xl font-semibold text-gray-800">
                    {response.rubric_scores.percentage.toFixed(1)}%
                  </p>
                  <p className="text-gray-600">
                    {response.rubric_scores.total_points} / {response.rubric_scores.max_points} points
                  </p>
                </div>
              </div>
            )}

            {/* Plagiarism / pattern analysis (heuristic, not web plagiarism lookup) */}
            {response.plagiarism_analysis && (
              <div
                className={`rounded-lg shadow-md p-6 border ${getPlagiarismRiskStyles(response.plagiarism_analysis.risk_level).panel}`}
              >
                <div className="flex flex-wrap items-center gap-3 mb-3">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Academic integrity (pattern check)
                  </h2>
                  <span
                    className={`text-sm font-semibold px-3 py-1 rounded-full uppercase tracking-wide ${getPlagiarismRiskStyles(response.plagiarism_analysis.risk_level).badge}`}
                  >
                    {response.plagiarism_analysis.risk_level} risk
                  </span>
                </div>
                <p className="text-sm text-gray-700 mb-4">{response.plagiarism_analysis.note}</p>
                {response.plagiarism_analysis.flags.length > 0 ? (
                  <ul className="space-y-3">
                    {response.plagiarism_analysis.flags.map((flag, index) => (
                      <li
                        key={index}
                        className="text-sm border border-gray-200 rounded-md p-3 bg-white/80"
                      >
                        <div className="font-medium text-gray-800 capitalize mb-1">
                          {flag.type.replace(/_/g, ' ')}
                          <span className="text-gray-500 font-normal ml-2">
                            (confidence {(flag.confidence * 100).toFixed(0)}%)
                          </span>
                        </div>
                        {flag.paragraph_indices.length > 0 && (
                          <p className="text-gray-600 text-xs mb-1">
                            Paragraphs: {formatParagraphRefs(flag.paragraph_indices)}
                          </p>
                        )}
                        <p className="text-gray-700">{flag.evidence}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-600">No pattern flags raised for this submission.</p>
                )}
              </div>
            )}

            {/* Processing Info */}
            {response.processing_info && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Processing Information
                </h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">File:</span>
                    <span className="ml-2 text-gray-600">{response.processing_info.file_name}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Type:</span>
                    <span className="ml-2 text-gray-600">{response.processing_info.file_type}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Length:</span>
                    <span className="ml-2 text-gray-600">{response.processing_info.text_length} chars</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Paragraphs:</span>
                    <span className="ml-2 text-gray-600">{response.processing_info.paragraph_count}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Model:</span>
                    <span className="ml-2 text-gray-600">{response.processing_info.model_used}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Overall Feedback */}
            {response.overall_feedback && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Overall Feedback
                </h2>
                <p className="text-gray-700 mb-4">{response.overall_feedback.summary}</p>

                {response.overall_feedback.key_strengths.length > 0 && (
                  <div className="mb-4">
                    <h3 className="font-medium text-gray-800 mb-2">Key Strengths:</h3>
                    <ul className="list-disc list-inside text-gray-600">
                      {response.overall_feedback.key_strengths.map((strength, index) => (
                        <li key={index}>{strength}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {response.overall_feedback.key_improvements.length > 0 && (
                  <div>
                    <h3 className="font-medium text-gray-800 mb-2">Key Improvements:</h3>
                    <ul className="list-disc list-inside text-gray-600">
                      {response.overall_feedback.key_improvements.map((improvement, index) => (
                        <li key={index}>{improvement}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Paragraph Feedback */}
            {response.paragraph_feedback && response.paragraph_feedback.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Paragraph-by-Paragraph Feedback
                </h2>
                <div className="space-y-4">
                  {response.paragraph_feedback.map((paragraph, index) => (
                    <div key={index} className="border border-gray-200 rounded-md p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-medium text-gray-800">
                          Paragraph {paragraph.paragraph_index + 1}
                        </h3>
                        <span className="text-sm font-semibold text-blue-600">
                          {paragraph.total_score} / {paragraph.max_score}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-3 italic">
                        "{paragraph.text}"
                      </p>
                      <p className="text-gray-700 mb-3">{paragraph.overall_feedback}</p>

                      {paragraph.strengths.length > 0 && (
                        <div className="mb-2">
                          <span className="text-sm font-medium text-green-700">Strengths: </span>
                          <span className="text-sm text-gray-600">
                            {paragraph.strengths.join(', ')}
                          </span>
                        </div>
                      )}

                      {paragraph.improvements.length > 0 && (
                        <div>
                          <span className="text-sm font-medium text-orange-700">Improvements: </span>
                          <span className="text-sm text-gray-600">
                            {paragraph.improvements.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggestions */}
            {response.suggestions && response.suggestions.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Suggestions for Improvement
                </h2>
                <ul className="space-y-2">
                  {response.suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-blue-600 mr-2">•</span>
                      <span className="text-gray-700">{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
