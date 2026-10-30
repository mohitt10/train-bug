import { useState } from 'react';

export function EditableText({
  initialValue = '',
  maxLength = null,
  placeholder = 'Write here…',
  onSave,
  onCancel,
  isSaving = false,
  minRows = 3,
}) {
  const [text, setText] = useState(initialValue);
  const [error, setError] = useState('');

  const trimmed = text.trim();
  const currentLength = text.length;
  const isOverLimit = maxLength ? currentLength > maxLength : false;
  const isEmpty = trimmed.length === 0;

  const handleSave = async (e) => {
    e.preventDefault();
    if (isEmpty) {
      setError('Content cannot be empty.');
      return;
    }
    if (isOverLimit) {
      setError(`Exceeds maximum limit of ${maxLength} characters.`);
      return;
    }

    try {
      setError('');
      await onSave(text.trim());
    } catch (err) {
      setError(err.message || 'Failed to save changes.');
    }
  };

  return (
    <form className="editable-text-form" onSubmit={handleSave}>
      <textarea
        className="form-textarea"
        rows={minRows}
        value={text}
        placeholder={placeholder}
        disabled={isSaving}
        onChange={(e) => {
          setText(e.target.value);
          if (error) setError('');
        }}
      />

      <div className="editable-text-footer">
        <div className="char-counter-wrapper">
          {maxLength ? (
            <span className={`counter ${isOverLimit ? 'counter-danger' : 'counter-muted'}`}>
              {currentLength} / {maxLength}
            </span>
          ) : (
            <span className="counter counter-muted">{currentLength} chars</span>
          )}
          {error && <span className="counter-error-inline">{error}</span>}
        </div>

        <div className="editable-text-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary btn-sm"
            disabled={isSaving || isEmpty || isOverLimit}
          >
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </form>
  );
}
