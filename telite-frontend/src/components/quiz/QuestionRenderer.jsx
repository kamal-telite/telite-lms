import React from 'react';

const QuestionRenderer = ({ question, currentAnswer, onChange }) => {
  if (!question) return null;

  return (
    <div className="bg-slate-50 p-6 rounded-lg border border-slate-100 mb-6">
      <div className="mb-4">
        <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full mb-3 uppercase tracking-wider">
          {question.type.replace('_', ' ')}
        </span>
        <h3 className="text-xl text-slate-800 font-medium leading-relaxed">
          {question.text}
        </h3>
      </div>

      <div className="space-y-3 mt-6">
        {question.type === 'multiple_choice' && [1, 2, 3, 4].map((opt) => (
          <label key={opt} className="flex items-center p-4 bg-white border border-slate-200 rounded-lg cursor-pointer hover:bg-indigo-50 hover:border-indigo-200 transition-colors">
            <input 
              type="radio" 
              name={`q-${question.id}`} 
              checked={currentAnswer === opt}
              onChange={() => onChange(opt)}
              className="w-5 h-5 text-indigo-600 border-gray-300 focus:ring-indigo-500"
            />
            <span className="ml-3 text-slate-700">Option {opt} placeholder text</span>
          </label>
        ))}

        {question.type === 'essay' && (
          <textarea
            value={currentAnswer || ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full p-4 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[200px]"
            placeholder="Type your answer here..."
          />
        )}
      </div>
    </div>
  );
};

export default QuestionRenderer;
