import React, { useState, useRef } from 'react'
import { Button, InlineNotification, FileUploader, FileUploaderItem, Loading } from '@carbon/react'
import { ArrowLeft, ArrowRight, DocumentAdd, CheckmarkFilled } from '@carbon/icons-react'
import { importExperiences } from '../../api/client'
import { downloadExperienceTemplate } from '../../utils/portfolio'
import { JTBD_0_DESCRIPTION, JTBD_0_TITLE } from '../../content/productMessaging'
import './ExperiencesStep.scss'

interface ExperiencesStepProps {
  onNext: () => void
  onBack: () => void
  onSkip: () => void
  companyName: string
}

const ExperiencesStep: React.FC<ExperiencesStepProps> = ({
  onNext,
  onBack,
  onSkip,
  companyName,
}) => {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [experiencesCount, setExperiencesCount] = useState(0)
  const [files, setFiles] = useState<File[]>([])

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setUploadError('Por favor selecciona un archivo Excel (.xlsx o .xls)')
      return
    }

    setIsUploading(true)
    setUploadError('')
    setUploadSuccess(false)
    setFiles([file])

    try {
      const result = await importExperiences(file, companyName)
      
      if (result.errors && result.errors.length > 0) {
        setUploadError(`Error: ${result.errors.join(', ')}`)
        setFiles([])
      } else {
        setExperiencesCount(result.imported)
        setUploadSuccess(true)
      }
    } catch (error: any) {
      setUploadError(error.response?.data?.detail || 'Error al cargar el archivo')
      setFiles([])
    } finally {
      setIsUploading(false)
    }
  }

  const handleFilesChange = (event: { target: { files: FileList | null } }) => {
    const file = event.target.files?.[0]
    if (file) {
      handleFileSelect({ target: { files: [file] } } as any)
    }
  }

  const handleRemoveFile = () => {
    setFiles([])
    setUploadError('')
    setUploadSuccess(false)
  }

  return (
    <div className="onboarding-experiences-step">
      <div className="onboarding-experiences-header">
        <Button
          kind="ghost"
          size="sm"
          onClick={onBack}
          renderIcon={ArrowLeft}
          className="onboarding-experiences-back"
        >
          Atrás
        </Button>
      </div>

      <div className="onboarding-experiences-content">
        <h2 className="onboarding-experiences-title">
          {JTBD_0_TITLE}
        </h2>
        
        <p className="onboarding-experiences-description">
          {JTBD_0_DESCRIPTION}
        </p>

        <div className="onboarding-experiences-upload">
          {isUploading ? (
            <div className="onboarding-upload-loading">
              <Loading description="Subiendo archivo..." withOverlay={false} />
              <p className="onboarding-upload-loading-text">Procesando archivo...</p>
            </div>
          ) : uploadSuccess ? (
            <div className="onboarding-upload-success">
              <div className="onboarding-upload-success-icon">
                <CheckmarkFilled size={32} />
              </div>
              <p className="onboarding-upload-success-text">
                ¡{experiencesCount} experiencias cargadas exitosamente!
              </p>
            </div>
          ) : (
            <FileUploader
              accept={['.xlsx', '.xls']}
              buttonKind="primary"
              buttonLabel="Seleccionar archivo Excel"
              filenameStatus="edit"
              iconDescription="Eliminar archivo"
              labelDescription="Solo archivos .xlsx o .xls"
              labelTitle="Subir archivo Excel"
              multiple={false}
              onChange={handleFilesChange}
              size="lg"
              className="onboarding-file-uploader"
            />
          )}

          {files.length > 0 && !uploadSuccess && (
            <div className="onboarding-files-list">
              {files.map((file, index) => (
                <FileUploaderItem
                  key={index}
                  name={file.name}
                  status="complete"
                  onDelete={handleRemoveFile}
                />
              ))}
            </div>
          )}

          {uploadError && (
            <InlineNotification
              kind="error"
              title="Error"
              subtitle={uploadError}
              lowContrast
              className="onboarding-experiences-error"
            />
          )}

          <div className="onboarding-upload-info">
            <p className="onboarding-upload-info-text">
              <strong>Formato requerido:</strong> Excel con columnas: Descripción, Entidad, Monto, Fecha
            </p>
            <Button
              kind="ghost"
              size="sm"
              onClick={(e) => {
                e.preventDefault()
                downloadExperienceTemplate()
              }}
              className="onboarding-download-template"
            >
              <DocumentAdd size={16} />
              Descargar plantilla
            </Button>
          </div>
        </div>

        <div className="onboarding-experiences-actions">
          <Button
            kind="ghost"
            size="md"
            onClick={onSkip}
            className="onboarding-experiences-skip"
          >
            Saltar este paso
          </Button>
          <Button
            size="lg"
            onClick={onNext}
            disabled={isUploading || !uploadSuccess}
            className="onboarding-experiences-continue"
            renderIcon={ArrowRight}
          >
            Continuar
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ExperiencesStep
