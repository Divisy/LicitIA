import React, { useState, useEffect } from 'react'
import {
  FileUploader,
  FileUploaderItem,
  Button,
  InlineNotification,
  Loading,
} from '@carbon/react'
import { Upload } from '@carbon/icons-react'
import { formatApiError, importRup } from '../api/client'
import './ExperienceUpload.scss'

interface ExperienceUploadProps {
  onUploadSuccess?: (count?: number) => void
  defaultCompanyName?: string
  showValueProposition?: boolean
}

const ExperienceUpload: React.FC<ExperienceUploadProps> = ({
  onUploadSuccess,
  defaultCompanyName = 'BEC',
}) => {
  const [file, setFile] = useState<File | null>(null)
  const [companyName, setCompanyName] = useState<string>(defaultCompanyName)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setCompanyName(defaultCompanyName)
  }, [defaultCompanyName])

  const handleFileChange = (event: { target: { files: FileList | null } }) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) return

    const name = selectedFile.name.toLowerCase()
    if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
      setMessage({
        type: 'error',
        text: 'Sube el certificado RUP en PDF, no la plantilla de experiencias.',
      })
      setFile(null)
      return
    }
    if (!name.endsWith('.pdf')) {
      setMessage({ type: 'error', text: 'Sube el certificado RUP en PDF.' })
      setFile(null)
      return
    }

    setFile(selectedFile)
    setMessage(null)
  }

  const handleRemoveFile = () => {
    setFile(null)
    setMessage(null)
  }

  const handleUpload = async () => {
    if (!file || !companyName.trim()) return

    const confirmed = window.confirm(
      'Esto actualiza la experiencia y los indicadores con este certificado. ¿Continuar?'
    )
    if (!confirmed) return

    setUploading(true)
    setMessage(null)

    try {
      const result = await importRup(file, companyName.trim())
      const extras: string[] = []
      if (result.capacity.liquidez != null) extras.push(`liquidez ${result.capacity.liquidez}`)
      if (result.capacity.endeudamiento != null) extras.push(`endeudamiento ${result.capacity.endeudamiento}`)
      setMessage({
        type: 'success',
        text: `${result.imported_experiences} contratos leídos del RUP${extras.length ? ` · ${extras.join(' · ')}` : ''}.`,
      })
      setFile(null)
      onUploadSuccess?.(result.imported_experiences)
    } catch (error) {
      setMessage({ type: 'error', text: formatApiError(error) })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="experience-upload">
      <div className="experience-upload__content">
        {uploading ? (
          <div className="experience-upload-loading">
            <Loading description="Extrayendo el RUP..." withOverlay={false} />
            <p className="experience-upload-loading-text">Leyendo experiencia e indicadores del certificado...</p>
          </div>
        ) : (
          <>
            <div className="experience-upload__dropzone">
              <FileUploader
                accept={['.pdf']}
                buttonKind="primary"
                buttonLabel="Seleccionar certificado RUP"
                filenameStatus="edit"
                iconDescription="Eliminar archivo"
                labelDescription="PDF vigente de la cámara de comercio (texto seleccionable, máx. 25 MB)"
                labelTitle=""
                multiple={false}
                onChange={handleFileChange}
                size="lg"
                className="experience-upload-file-uploader"
              />
            </div>

            {file && (
              <div className="experience-upload-file-list">
                <FileUploaderItem
                  name={file.name}
                  status="complete"
                  onDelete={handleRemoveFile}
                  size={file.size}
                />
              </div>
            )}

            {message && (
              <InlineNotification
                kind={message.type === 'success' ? 'success' : 'error'}
                title={message.type === 'success' ? 'RUP cargado' : 'Error'}
                subtitle={message.text}
                lowContrast={false}
                className="experience-upload-message"
                onClose={() => setMessage(null)}
              />
            )}

            <div className="experience-upload__actions">
              <Button
                type="button"
                size="lg"
                onClick={handleUpload}
                disabled={!file || uploading || !companyName.trim()}
                renderIcon={Upload}
                className="experience-upload-button"
              >
                {uploading ? 'Extrayendo...' : 'Cargar RUP'}
              </Button>
            </div>
            <p className="experience-upload__dropzone-hint">
              Esto reemplaza las experiencias e indicadores de la empresa con los de este certificado.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

export default ExperienceUpload
