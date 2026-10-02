import React, { useState } from 'react'
import { Button, InlineNotification, FileUploader, FileUploaderItem, Loading } from '@carbon/react'
import { ArrowLeft, ArrowRight, CheckmarkFilled } from '@carbon/icons-react'
import { importRup } from '../../api/client'
import { JTBD_0_DESCRIPTION, JTBD_0_TITLE } from '../../content/productMessaging'
import './ExperiencesStep.scss'

interface RupUploadStepProps {
  onNext: () => void
  onBack: () => void
  onSkip: () => void
  companyName: string
}

function apiErrorMessage(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return 'Error al cargar el RUP'
}

const RupUploadStep: React.FC<RupUploadStepProps> = ({
  onNext,
  onBack,
  onSkip,
  companyName,
}) => {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [experiencesCount, setExperiencesCount] = useState(0)
  const [capacitySummary, setCapacitySummary] = useState('')
  const [files, setFiles] = useState<File[]>([])

  const handleFile = async (file: File) => {
    const name = file.name.toLowerCase()
    if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
      setUploadError('Sube el certificado RUP en PDF, no la plantilla de experiencias.')
      return
    }
    if (!name.endsWith('.pdf')) {
      setUploadError('Sube el certificado RUP en PDF.')
      return
    }

    setIsUploading(true)
    setUploadError('')
    setUploadSuccess(false)
    setFiles([file])

    try {
      const result = await importRup(file, companyName)
      setExperiencesCount(result.imported_experiences)
      const bits: string[] = []
      if (result.capacity.liquidez != null) bits.push(`liquidez ${result.capacity.liquidez}`)
      if (result.capacity.endeudamiento != null) bits.push(`endeudamiento ${result.capacity.endeudamiento}`)
      setCapacitySummary(bits.join(' · '))
      setUploadSuccess(true)
    } catch (error) {
      setUploadError(apiErrorMessage(error))
      setFiles([])
    } finally {
      setIsUploading(false)
    }
  }

  const handleFilesChange = (event: { target: { files: FileList | null } }) => {
    const file = event.target.files?.[0]
    if (file) {
      void handleFile(file)
    }
  }

  const handleRemoveFile = () => {
    setFiles([])
    setUploadError('')
    setUploadSuccess(false)
    setCapacitySummary('')
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
        <h2 className="onboarding-experiences-title">{JTBD_0_TITLE}</h2>
        <p className="onboarding-experiences-description">{JTBD_0_DESCRIPTION}</p>

        <div className="onboarding-experiences-upload">
          {isUploading ? (
            <div className="onboarding-upload-loading">
              <Loading description="Extrayendo el RUP..." withOverlay={false} />
              <p className="onboarding-upload-loading-text">Leyendo experiencia e indicadores del certificado...</p>
            </div>
          ) : uploadSuccess ? (
            <div className="onboarding-upload-success">
              <div className="onboarding-upload-success-icon">
                <CheckmarkFilled size={32} />
              </div>
              <p className="onboarding-upload-success-text">
                {experiencesCount} contratos leídos del RUP
              </p>
              {capacitySummary && (
                <p className="onboarding-experiences-description">{capacitySummary}</p>
              )}
            </div>
          ) : (
            <FileUploader
              accept={['.pdf']}
              buttonKind="primary"
              buttonLabel="Seleccionar certificado RUP"
              filenameStatus="edit"
              iconDescription="Eliminar archivo"
              labelDescription="PDF del certificado vigente (texto seleccionable, máx. 25 MB)"
              labelTitle="Cargar RUP"
              multiple={false}
              onChange={handleFilesChange}
              size="lg"
              className="onboarding-file-uploader"
            />
          )}

          {files.length > 0 && !uploadSuccess && (
            <div className="onboarding-files-list">
              {files.map((file) => (
                <FileUploaderItem
                  key={file.name}
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
              Esto actualiza la experiencia y los indicadores con este certificado.
              Usa el PDF que descargas en la cámara de comercio, no un escaneo de foto.
            </p>
          </div>
        </div>

        <div className="onboarding-experiences-actions">
          <Button
            kind="ghost"
            size="md"
            onClick={onSkip}
            className="onboarding-experiences-skip"
          >
            Explorar sin personalizar
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

export default RupUploadStep
