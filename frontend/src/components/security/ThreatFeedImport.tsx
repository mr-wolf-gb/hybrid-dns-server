import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { CloudArrowDownIcon } from '@heroicons/react/24/outline'
import { rpzService } from '@/services/api'
import { Modal, Button, Input, Select } from '@/components/ui'
import { toast } from 'react-toastify'

interface ThreatFeedImportProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

interface ImportFormData {
  category: string
  url: string
}

const ThreatFeedImport: React.FC<ThreatFeedImportProps> = ({ isOpen, onClose, onSuccess }) => {
  const [importResults, setImportResults] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<ImportFormData>({
    defaultValues: {
      category: 'malware',
      url: '',
    },
  })

  // Import rules mutation
  const importMutation = useMutation({
    mutationFn: ({ category, url }: ImportFormData) => rpzService.importRules(category, url),
    onSuccess: (response) => {
      const imported = response.data.data.imported
      setImportResults(`Successfully imported ${imported} threat rules`)
      toast.success(`Imported ${imported} threat rules`)
      onSuccess()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to import threat feed')
    },
  })

  const onSubmit = (data: ImportFormData) => {
    setImportResults(null)
    importMutation.mutate(data)
  }

  const handleClose = () => {
    reset()
    setImportResults(null)
    onClose()
  }

  const loadPresetUrl = (preset: string) => {
    const presetUrls: Record<string, string> = {
      'malware-domains': 'https://mirror1.malwaredomains.com/files/domains.txt',
      'phishing-army': 'https://phishing.army/download/phishing_army_blocklist_extended.txt',
      'someonewhocares': 'https://someonewhocares.org/hosts/zero/hosts',
      'hphost-malware': 'https://hosts-file.net/grm.txt',
      'abuse-ch': 'https://urlhaus.abuse.ch/downloads/hostfile/',
    }

    if (presetUrls[preset]) {
      setValue('url', presetUrls[preset])
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Import Threat Feed"
      size="lg"
    >
      <div className="space-y-6">
        {!importResults ? (
          <>
            <div className="text-center">
              <CloudArrowDownIcon className="mx-auto h-12 w-12 text-blue-500" />
              <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                Import Threat Intelligence
              </h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Import domains from public threat intelligence feeds
              </p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div className="grid grid-cols-1 gap-6">
                <Select
                  label="Category"
                  options={[
                    { value: 'malware', label: 'Malware Domains' },
                    { value: 'phishing', label: 'Phishing Sites' },
                    { value: 'custom', label: 'Custom Category' },
                  ]}
                  {...register('category', { required: 'Category is required' })}
                  error={errors.category?.message}
                />

                <Input
                  label="Feed URL"
                  type="url"
                  placeholder="https://example.com/threat-feed.txt"
                  {...register('url', {
                    required: 'Feed URL is required',
                    pattern: {
                      value: /^https?:\/\/.+/,
                      message: 'Must be a valid HTTP/HTTPS URL',
                    },
                  })}
                  error={errors.url?.message}
                  helperText="URL to a text file containing domains (one per line)"
                />
              </div>

              {/* Preset feeds */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                  Popular Threat Feeds:
                </h4>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <button
                    type="button"
                    className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                    onClick={() => loadPresetUrl('malware-domains')}
                  >
                    Malware Domains List
                  </button>
                  <button
                    type="button"
                    className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                    onClick={() => loadPresetUrl('phishing-army')}
                  >
                    Phishing Army
                  </button>
                  <button
                    type="button"
                    className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                    onClick={() => loadPresetUrl('someonewhocares')}
                  >
                    SomeoneWhoCares Hosts
                  </button>
                  <button
                    type="button"
                    className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                    onClick={() => loadPresetUrl('hphost-malware')}
                  >
                    HP Hosts Malware
                  </button>
                  <button
                    type="button"
                    className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                    onClick={() => loadPresetUrl('abuse-ch')}
                  >
                    Abuse.ch URLhaus
                  </button>
                </div>
              </div>

              {/* Warning */}
              <div className="bg-yellow-50 dark:bg-yellow-900/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                  Important Notes:
                </h4>
                <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                  <li>• Large feeds may take several minutes to import</li>
                  <li>• Duplicate domains will be automatically filtered</li>
                  <li>• Imported rules will be marked with the selected category</li>
                  <li>• BIND configuration will be reloaded after import</li>
                </ul>
              </div>

              <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
                <Button variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={importMutation.isPending}
                >
                  Import Feed
                </Button>
              </div>
            </form>
          </>
        ) : (
          <>
            {/* Success state */}
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 dark:bg-green-900/30">
                <CloudArrowDownIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                Import Complete
              </h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {importResults}
              </p>
            </div>

            <div className="flex justify-center">
              <Button onClick={handleClose}>
                Done
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

export default ThreatFeedImport