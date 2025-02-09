# Copyright 2021 kubeflow.org
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from kfp import components, dsl

fairness_check_ops = components.load_component_from_url('https://raw.githubusercontent.com/Trusted-AI/AIF360/master/mlops/kubeflow/bias_detector_pytorch/component.yaml')
robustness_check_ops = components.load_component_from_url('https://raw.githubusercontent.com/Trusted-AI/adversarial-robustness-toolbox/main/utils/mlops/kubeflow/robustness_evaluation_fgsm_pytorch/component.yaml')

@dsl.pipeline(
    name="Launch trusted-ai pipeline",
    description="An example for trusted-ai integration."
)
def trusted_ai(
        namespace:str = "anonymous",
        fgsm_attack_epsilon:str = '0.2',
        model_class_file:str = 'PyTorchModel.py',
        model_class_name:str = 'ThreeLayerCNN',
        feature_testset_path:str = 'processed_data/X_test.npy',
        label_testset_path:str = 'processed_data/y_test.npy',
        protected_label_testset_path:str = 'processed_data/p_test.npy',
        favorable_label:str = '0.0',
        unfavorable_label:str = '1.0',
        privileged_groups:str = "[{'race': 0.0}]",
        unprivileged_groups:str = "[{'race': 4.0}]",
        loss_fn:str = 'torch.nn.CrossEntropyLoss()',
        optimizer:str = 'torch.optim.Adam(model.parameters(), lr=0.001)',
        clip_values:str = '(0, 1)',
        nb_classes:str = '2',
        input_shape:str = '(1,3,64,64)'):
    job_manifest = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": "trusted-ai-train-job",
            "namespace": namespace
        },
        "spec": {
            "ttlSecondsAfterFinished": 100,
            "template": {
                "metadata": {
                    "annotations": {
                        "sidecar.istio.io/inject": "false"
                    }
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {"name": "classification-training",
                         "image": "aipipeline/gender-classification:latest",
                         "command": [
                             "python", "-u", "gender_classification_training.py", "--data_bucket", "mlpipeline",
                             "--result_bucket", "mlpipeline"
                         ],
                         "env": [{'name': 'S3_ENDPOINT', 'value': 'minio-service.kubeflow:9000'}]
                         }
                    ],
                }
            }
        }
    }
    train_step = dsl.ResourceOp(
        name="trust-ai-train-step",
        k8s_resource=job_manifest,
        action='create',
        success_condition='status.succeeded > 0',
        failure_condition='status.failed > 0')

    fairness_check = fairness_check_ops(model_id='training-example',
                                        model_class_file=model_class_file,
                                        model_class_name=model_class_name,
                                        feature_testset_path=feature_testset_path,
                                        label_testset_path=label_testset_path,
                                        protected_label_testset_path=protected_label_testset_path,
                                        favorable_label=favorable_label,
                                        unfavorable_label=unfavorable_label,
                                        privileged_groups=privileged_groups,
                                        unprivileged_groups=unprivileged_groups,
                                        data_bucket_name='mlpipeline',
                                        result_bucket_name='mlpipeline').after(train_step).set_image_pull_policy("Always")
    robustness_check = robustness_check_ops(model_id='training-example',
                                            epsilon=fgsm_attack_epsilon,
                                            model_class_file=model_class_file,
                                            model_class_name=model_class_name,
                                            feature_testset_path=feature_testset_path,
                                            label_testset_path=label_testset_path,
                                            loss_fn=loss_fn,
                                            optimizer=optimizer,
                                            clip_values=clip_values,
                                            nb_classes=nb_classes,
                                            input_shape=input_shape,
                                            data_bucket_name='mlpipeline',
                                            result_bucket_name='mlpipeline').after(train_step).set_image_pull_policy("Always")


if __name__ == '__main__':
    from kfp_tekton.compiler import TektonCompiler
    TektonCompiler().compile(trusted_ai, __file__.replace('.py', '.yaml'))
