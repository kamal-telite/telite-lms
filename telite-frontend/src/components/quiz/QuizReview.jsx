import React from 'react';

const QuizReview = ({ attempt }) => {
  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-xl shadow-lg border border-slate-200">
      <div className="text-center mb-10 pb-6 border-b border-slate-100">
        <h2 className="text-3xl font-bold text-slate-800 mb-2">Quiz Results</h2>
        <div className="inline-flex items-center justify-center space-x-2 mt-4">
          <span className="text-5xl font-black text-indigo-600">85</span>
          <span className="text-xl text-slate-400 font-medium">/ 100</span>
        </div>
        <p className="mt-4 text-emerald-600 font-semibold bg-emerald-50 inline-block px-4 py-1 rounded-full">
          Status: Passed
        </p>
      </div>

      <div className="space-y-8">
        {[1, 2].map((q) => (
          <div key={q} className="bg-slate-50 p-6 rounded-lg border border-slate-200">
            <div className="flex justify-between items-start mb-4">
              <h4 className="text-lg font-medium text-slate-800">Question {q}</h4>
              <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full">
                10 / 10 points
              </span>
            </div>
            <p className="text-slate-600 mb-4">What is the capital of France?</p>
            
            <div className="space-y-2">
              <div className="p-3 bg-white border border-green-300 rounded-lg flex items-center">
                <div className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center mr-3 text-sm">✓</div>
                <span className="text-slate-700">Paris (Your Answer)</span>
              </div>
            </div>

            <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg">
              <h5 className="text-sm font-semibold text-blue-800 mb-1">Instructor Feedback</h5>
              <p className="text-sm text-blue-700">Excellent work identifying the capital correctly.</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default QuizReview;
