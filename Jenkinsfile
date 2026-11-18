pipeline {
  agent any

  environment {
    PROJECT = 'fcm-test-7e087'          // ID del proyecto de Firebase / Google Cloud
    REGION  = 'us-central1'
    SERVICE = 'nomina-rd'                  // debe coincidir con serviceId de firebase.json
    IMAGE   = "us-central1-docker.pkg.dev/fcm-test-7e087/nomina-rd/nomina-rd:${BUILD_NUMBER}"
    CLOUDSQL_INSTANCE = ''                 // 'proyecto:region:instancia' si usas Cloud SQL; vacío si no
  }

  stages {
    stage('Pruebas') {
      steps {
        sh '''
          python3 -m venv venv
          . venv/bin/activate
          pip install -q -r requirements-dev.txt
          pytest -q
        '''
      }
    }

    stage('Construir imagen') {
      steps { sh 'docker build -t $IMAGE .' }
    }

    stage('Subir imagen') {
      steps {
        withCredentials([file(credentialsId: 'gcp-key', variable: 'KEY')]) {
          sh '''
            gcloud auth activate-service-account --key-file=$KEY
            gcloud auth configure-docker us-central1-docker.pkg.dev -q
            docker push $IMAGE
          '''
        }
      }
    }

    stage('Desplegar') {
      steps {
        withCredentials([
          file(credentialsId: 'gcp-key', variable: 'KEY'),
          string(credentialsId: 'flask-secret-key', variable: 'SECRET_KEY'),
          string(credentialsId: 'database-url', variable: 'DATABASE_URL'),
          string(credentialsId: 'admin-email', variable: 'ADMIN_EMAIL'),
          string(credentialsId: 'admin-password', variable: 'ADMIN_PASSWORD')
        ]) {
          sh '''
            gcloud auth activate-service-account --key-file=$KEY

            # "^##^" cambia el separador de variables para que las claves puedan contener comas
            gcloud run deploy $SERVICE \
              --image $IMAGE \
              --region $REGION \
              --project $PROJECT \
              --allow-unauthenticated \
              --max-instances 2 \
              --memory 512Mi \
              ${CLOUDSQL_INSTANCE:+--add-cloudsql-instances $CLOUDSQL_INSTANCE} \
              --set-env-vars "^##^APP_ENV=production##SECRET_KEY=$SECRET_KEY##DATABASE_URL=$DATABASE_URL##ADMIN_EMAIL=$ADMIN_EMAIL##ADMIN_PASSWORD=$ADMIN_PASSWORD"

            export GOOGLE_APPLICATION_CREDENTIALS=$KEY
            firebase deploy --only hosting --project $PROJECT
          '''
        }
      }
    }

    stage('Verificar') {
      steps {
        sh '''
          for i in 1 2 3 4 5; do
            curl -fsS https://$PROJECT.web.app/healthz && exit 0
            sleep 10
          done
          exit 1
        '''
      }
    }
  }

  post {
    success { echo 'Nómina RD desplegado correctamente' }
    failure { echo 'Falló una etapa: revisa el Console Output' }
  }
}
