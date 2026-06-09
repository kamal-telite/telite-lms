import React, { useState } from 'react';

const GradingDashboard = () => {
  const [selectedAttempt, setSelectedAttempt] = useState(null);

  const pendingAttempts = [
    { id: 101, student: 'Alice Smith', quiz: 'Python Basics', submittedAt: '2 hours ago', status: 'Needs Grading' },
    { id: 102, student: 'Bob Jones', quiz: 'React Fundamentals', submittedAt: '5 hours ago', status: 'Needs Grading' },
  ];

  return (
    <div className="flex h-[800px] bg-slate-50 border border-slate-200 rounded-xl overflow-hidden">
      {/* Sidebar Queue */}
      <div className="w-1/3 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-lg font-bold text-slate-800">Pending Grading</h2>
          <p className="text-sm text-slate-500">{pendingAttempts.length} submissions to review</p>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {pendingAttempts.map(attempt => (
            <div 
              key={attempt.id}
              onClick={() => setSelectedAttempt(attempt)}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${selectedAttempt?.id === attempt.id ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300'}`}
            >
              <div className="flex justify-between mb-1">
                <span className="font-semibold text-slate-800">{attempt.student}</span>
                <span className="text-xs font-medium px-2 py-1 bg-amber-100 text-amber-700 rounded-full">{attempt.status}</span>
              </div>
              <div className="text-sm text-slate-600 mb-2">{attempt.quiz}</div>
              <div className="text-xs text-slate-400">Submitted {attempt.submittedAt}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Grading Area */}
      <div className="flex-1 flex flex-col bg-slate-50">
        {selectedAttempt ? (
          <>
            <div className="p-6 border-b border-slate-200 bg-white">
              <h2 className="text-2xl font-bold text-slate-800">{selectedAttempt.student}'s Submission</h2>
              <p className="text-slate-500">{selectedAttempt.quiz}</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                <h4 className="font-semibold text-slate-800 mb-2">Question 1 (Essay)</h4>
                <p className="text-slate-600 mb-4">Explain the concept of closures in JavaScript.</p>
                <div className="p-4 bg-slate-50 border border-slate-100 rounded-lg text-slate-700 italic mb-6">
                  "A closure is the combination of a function bundled together (enclosed) with references to its surrounding state (the lexical environment). In other words, a closure gives you access to an outer function's scope from an inner function."
                </div>

                <div className="border-t border-slate-100 pt-6">
                  <h5 className="font-medium text-slate-800 mb-3">Grading & Feedback</h5>
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="col-span-1">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Points (out of 10)</label>
                      <input type="number" className="w-full border border-slate-300 rounded-md p-2 focus:ring-indigo-500 focus:border-indigo-500" defaultValue="8" />
                    </div>
                    <div className="col-span-3">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Feedback</label>
                      <textarea className="w-full border border-slate-300 rounded-md p-2 focus:ring-indigo-500 focus:border-indigo-500" rows="3" placeholder="Enter feedback here..."></textarea>
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors">
                    Save Grade
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            Select a submission from the queue to start grading
          </div>
        )}
      </div>
    </div>
  );
};

export default GradingDashboard;
