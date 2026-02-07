/**
 * Memory Form Component
 *
 * Form for creating and editing memories.
 */
import { useState, useEffect } from 'react';
import { Save, X, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useCreateMemory, useUpdateMemory, useMemory } from '@/hooks/use-memories';
import { MEMORY_TYPES, type MemoryType, type Memory } from '@/types';
import { cn } from '@/lib/utils';

interface MemoryFormProps {
  mode: 'create' | 'edit';
  type?: string;
  id?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

interface MetadataField {
  key: string;
  value: string;
}

// Default metadata fields by type
const DEFAULT_METADATA_FIELDS: Record<string, string[]> = {
  requirements: ['requirement_id', 'title', 'priority', 'status'],
  design: ['design_type', 'title', 'decision', 'rationale'],
  code_pattern: ['pattern_name', 'pattern_type', 'language'],
  component: ['component_name', 'component_type', 'path'],
  function: ['function_name', 'file_path', 'language', 'signature'],
  test_history: ['test_name', 'test_file', 'result', 'duration'],
  session: ['session_id', 'phase', 'summary'],
  user_preference: ['preference_key', 'category']
};

export function MemoryForm({ mode, type, id, onSuccess, onCancel }: MemoryFormProps) {
  const [memoryType, setMemoryType] = useState<MemoryType>(
    (type as MemoryType) || 'requirements'
  );
  const [content, setContent] = useState('');
  const [metadataFields, setMetadataFields] = useState<MetadataField[]>([]);
  const [relationships, setRelationships] = useState<Array<{ targetId: string; type: string }>>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Load existing memory in edit mode
  const { data: existingMemory, isLoading } = useMemory(type || '', id || '');

  const createMemory = useCreateMemory();
  const updateMemory = useUpdateMemory();

  // Initialize form with existing data
  useEffect(() => {
    if (mode === 'edit' && existingMemory) {
      setMemoryType(existingMemory.type);
      setContent(existingMemory.content);
      setMetadataFields(
        Object.entries(existingMemory.metadata || {}).map(([key, value]) => ({
          key,
          value: typeof value === 'string' ? value : JSON.stringify(value)
        }))
      );
    } else if (mode === 'create') {
      // Set default metadata fields for the type
      const defaults = DEFAULT_METADATA_FIELDS[memoryType] || [];
      setMetadataFields(defaults.map(key => ({ key, value: '' })));
    }
  }, [mode, existingMemory, memoryType]);

  // Track unsaved changes
  useEffect(() => {
    if (mode === 'edit' && existingMemory) {
      const contentChanged = content !== existingMemory.content;
      const metadataChanged = JSON.stringify(
        metadataFields.reduce((acc, f) => ({ ...acc, [f.key]: f.value }), {})
      ) !== JSON.stringify(existingMemory.metadata);
      setHasUnsavedChanges(contentChanged || metadataChanged);
    } else if (mode === 'create') {
      setHasUnsavedChanges(content.length > 0);
    }
  }, [content, metadataFields, mode, existingMemory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const metadata = metadataFields
      .filter(f => f.key && f.value)
      .reduce((acc, f) => {
        try {
          acc[f.key] = JSON.parse(f.value);
        } catch {
          acc[f.key] = f.value;
        }
        return acc;
      }, {} as Record<string, unknown>);

    if (mode === 'create') {
      createMemory.mutate(
        {
          type: memoryType,
          content,
          metadata,
          relationships: relationships.length > 0 ? relationships : undefined
        },
        { onSuccess }
      );
    } else if (id && type) {
      updateMemory.mutate(
        {
          type,
          id,
          data: {
            content,
            metadata,
            relationships: relationships.length > 0 ? relationships : undefined
          }
        },
        { onSuccess }
      );
    }
  };

  const handleCancel = () => {
    if (hasUnsavedChanges) {
      if (confirm('You have unsaved changes. Are you sure you want to cancel?')) {
        onCancel?.();
      }
    } else {
      onCancel?.();
    }
  };

  const addMetadataField = () => {
    setMetadataFields([...metadataFields, { key: '', value: '' }]);
  };

  const removeMetadataField = (index: number) => {
    setMetadataFields(metadataFields.filter((_, i) => i !== index));
  };

  const updateMetadataField = (index: number, field: 'key' | 'value', value: string) => {
    const newFields = [...metadataFields];
    newFields[index][field] = value;
    setMetadataFields(newFields);
  };

  const addRelationship = () => {
    setRelationships([...relationships, { targetId: '', type: '' }]);
  };

  const removeRelationship = (index: number) => {
    setRelationships(relationships.filter((_, i) => i !== index));
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-10 bg-muted rounded" />
        <div className="h-32 bg-muted rounded" />
        <div className="h-20 bg-muted rounded" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Type Selection */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Memory Type</label>
        <select
          value={memoryType}
          onChange={(e) => setMemoryType(e.target.value as MemoryType)}
          disabled={mode === 'edit'}
          className={cn(
            "w-full h-10 rounded-md border border-input bg-background px-3 text-sm",
            mode === 'edit' && "opacity-50 cursor-not-allowed"
          )}
        >
          {MEMORY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace('_', ' ')}
            </option>
          ))}
        </select>
        {mode === 'edit' && (
          <p className="text-xs text-muted-foreground">Type cannot be changed after creation</p>
        )}
      </div>

      {/* Content */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Content *</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Enter memory content..."
          required
          className={cn(
            "w-full min-h-[200px] rounded-md border border-input bg-background p-3 text-sm",
            "font-mono resize-y",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          )}
        />
      </div>

      {/* Metadata */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Metadata</label>
          <Button type="button" variant="ghost" size="sm" onClick={addMetadataField}>
            <Plus className="h-4 w-4 mr-1" />
            Add Field
          </Button>
        </div>
        <div className="space-y-2">
          {metadataFields.map((field, index) => (
            <div key={index} className="flex gap-2">
              <Input
                placeholder="Key"
                value={field.key}
                onChange={(e) => updateMetadataField(index, 'key', e.target.value)}
                className="w-1/3"
              />
              <Input
                placeholder="Value"
                value={field.value}
                onChange={(e) => updateMetadataField(index, 'value', e.target.value)}
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeMetadataField(index)}
              >
                <Trash2 className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
          {metadataFields.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-2">
              No metadata fields. Click "Add Field" to add one.
            </p>
          )}
        </div>
      </div>

      {/* Relationships */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Relationships</label>
          <Button type="button" variant="ghost" size="sm" onClick={addRelationship}>
            <Plus className="h-4 w-4 mr-1" />
            Add Relationship
          </Button>
        </div>
        <div className="space-y-2">
          {relationships.map((rel, index) => (
            <div key={index} className="flex gap-2">
              <Input
                placeholder="Target Memory ID"
                value={rel.targetId}
                onChange={(e) => {
                  const newRels = [...relationships];
                  newRels[index].targetId = e.target.value;
                  setRelationships(newRels);
                }}
                className="flex-1"
              />
              <select
                value={rel.type}
                onChange={(e) => {
                  const newRels = [...relationships];
                  newRels[index].type = e.target.value;
                  setRelationships(newRels);
                }}
                className="w-40 h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">Select type...</option>
                <option value="IMPLEMENTS">IMPLEMENTS</option>
                <option value="DEPENDS_ON">DEPENDS_ON</option>
                <option value="EXTENDS">EXTENDS</option>
                <option value="CALLS">CALLS</option>
                <option value="TESTS">TESTS</option>
                <option value="RELATED_TO">RELATED_TO</option>
              </select>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeRelationship(index)}
              >
                <Trash2 className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
          {relationships.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-2">
              No relationships. Click "Add Relationship" to link to other memories.
            </p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-4 border-t">
        <Button
          type="submit"
          disabled={createMemory.isPending || updateMemory.isPending || !content}
        >
          <Save className="h-4 w-4 mr-2" />
          {createMemory.isPending || updateMemory.isPending
            ? 'Saving...'
            : mode === 'create'
              ? 'Create Memory'
              : 'Save Changes'}
        </Button>
        <Button type="button" variant="outline" onClick={handleCancel}>
          <X className="h-4 w-4 mr-2" />
          Cancel
        </Button>
      </div>

      {/* Unsaved changes indicator */}
      {hasUnsavedChanges && (
        <p className="text-xs text-amber-600">You have unsaved changes</p>
      )}
    </form>
  );
}

export default MemoryForm;
