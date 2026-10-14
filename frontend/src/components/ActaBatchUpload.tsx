import React, { useState } from 'react'
import {
  Button,
  FileUploader,
  InlineNotification,
  Loading,
} from '@carbon/react'
import { Upload } from '@carbon/icons-react'
import { assignActaToContract, formatApiError } from '../api/client'
import './ActaBatchUpload.scss'

interface ActaBatchUploadProps {
  companyName: string
  onAssigned?: () => void
}

type RowResult = {
  filename: string
  kind: 'assigned' | 'unmatched' | 'ambiguous' | 'error'
  text: string
}

const ActaBatchUpload: React.FC<ActaBatchUploadProps> = ({ companyName, onAssigned }) => {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState('')
  const [results, setResults] = useState<RowResult[]>([])
  const [summary, setSummary] = useState<string | null>(null)

  const handleFileChange = (event: { target: { files: FileList | null } }) => {
    const selected = Array.from(event.target.files || [])
    const pdfs = selected.filter((file) => file.name.toLowerCase().endsWith('.pdf'))
    setFiles(pdfs)
    setResults([])
    setSummary(
      selected.length !== pdfs.length
        ? 'Solo se cargan actas en PDF. Los otros archivos se omitieron.'
        : null
    )
  }

  const handleUpload = async () => {
    if (!files.length || uploading) return
    setUploading(true)
    setResults([])
    setSummary(null)
    const next: RowResult[] = []
    let assigned = 0
    try {
      for (let index = 0; index < files.length; index += 1) {
        const file = files[index]
        setProgress(`Leyendo acta ${index + 1} de ${files.length}`)
        try {
          const result = await assignActaToContract(file, companyName)
          if (result.status === 'assigned') {
            assigned += 1
            next.push({
              filename: file.name,
              kind: 'assigned',
              text: result.detail || `Guardada en ${result.matched_contract_numbers.join(', ')}`,
            })
          } else if (result.status === 'ambiguous') {
            next.push({ filename: file.name, kind: 'ambiguous', text: result.detail || 'Varios contratos coinciden.' })
          } else {
            next.push({
              filename: file.name,
              kind: 'unmatched',
              text: result.detail || 'No coincide con un contrato del RUP.',
            })
          }
        } catch (error) {
          next.push({
            filename: file.name,
            kind: 'error',
            text: formatApiError(error, 'No se pudo leer el acta.'),
          })
        }
        setResults([...next])
      }
      setSummary(
        `${assigned} de ${files.length} actas quedaron en su contrato.`
      )
      if (assigned > 0) onAssigned?.()
      setFiles([])
    } finally {
      setUploading(false)
      setProgress('')
    }
  }

  return (
    <div className="acta-batch">
      <p className="acta-batch__lead">
        Si son muchas, súbelas juntas. LicitIA lee el número de contrato de cada acta y la guarda en esa fila, con el objeto.
      </p>
      {uploading ? (
        <div className="acta-batch__loading">
          <Loading description={progress || 'Leyendo actas'} withOverlay={false} />
          <p>{progress}</p>
        </div>
      ) : (
        <>
          <FileUploader
            accept={['.pdf']}
            buttonKind="tertiary"
            buttonLabel="Seleccionar actas"
            filenameStatus="edit"
            iconDescription="Quitar"
            labelDescription="Uno o varios PDF, máximo 25 MB cada uno"
            labelTitle=""
            multiple
            onChange={handleFileChange}
            size="md"
          />
          {files.length > 0 && (
            <p className="acta-batch__count">{files.length} actas listas para asignar</p>
          )}
          <Button
            type="button"
            size="md"
            kind="primary"
            renderIcon={Upload}
            disabled={!files.length}
            onClick={handleUpload}
          >
            Asignar actas a los contratos
          </Button>
        </>
      )}
      {summary && (
        <InlineNotification
          kind="success"
          title="Actas leídas"
          subtitle={summary}
          lowContrast
          onClose={() => setSummary(null)}
        />
      )}
      {results.length > 0 && (
        <ul className="acta-batch__results">
          {results.map((row) => (
            <li key={row.filename} className={`acta-batch__result acta-batch__result--${row.kind}`}>
              <strong>{row.filename}</strong>
              <span>{row.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default ActaBatchUpload
