rest_api_version = 3  # type: int

def update_param(name, param):
    if name == 'algorithm_params':
        param['type'] = 'KeyValue'
        param['default_value'] = None
        return param
    return None  # param untouched

def class_extensions():    
    def _extract_x_from_model(self):
        """
        extract admissible features from an Infogram model.
        
        :return: List of predictors that are considered admissible
        """
        features = self._model_json.get('output', {}).get('admissible_features')
        if features is None:
            raise ValueError("model %s doesn't have any admissible features" % self.key)
        return set(features)
        
    def plot(self, train=True, valid=False, xval=False, figsize=(10, 10), title="Infogram", legend_on=False, server=False):
        """
        Plot the infogram.  By default, it will plot the infogram calculated from training dataset.  
        Note that the frame rel_cmi_frame contains the following columns:
        - 0: predictor names
        - 1: admissible 
        - 2: admissible index
        - 3: relevance-index or total information
        - 4: safety-index or net information, normalized from 0 to 1
        - 5: safety-index or net information not normalized
        
        :param train: True if infogram is generated from training dataset
        :param valid: True if infogram is generated from validation dataset
        :param xval: True if infogram is generated from cross-validation holdout dataset
        :param figsize: size of infogram plot
        :param title: string to denote title of the plot
        :param legend_on: legend text is included if True
        :param server: True will not generate plot, False will produce plot
        :return: infogram plot if server=True or None if server=False
        """
        
        plt = get_matplotlib_pyplot(server, raise_if_not_available=True)
        polycoll = get_polycollection(server, raise_if_not_available=True)
        if not can_use_numpy():
            raise ImportError("numpy is required for Infogram.")
        import numpy as np
        
        if train:
            rel_cmi_frame = self.get_admissible_score_frame()
            if rel_cmi_frame is None:
                raise H2OValueError("Cannot locate the H2OFrame containing the infogram data from training dataset.")
        if valid:
            rel_cmi_frame_valid = self.get_admissible_score_frame(valid=True)
            if rel_cmi_frame_valid is None:
                raise H2OValueError("Cannot locate the H2OFrame containing the infogram data from validation dataset.")
        if xval:
            rel_cmi_frame_xval = self.get_admissible_score_frame(xval=True)
            if rel_cmi_frame_xval is None:
                raise H2OValueError("Cannot locate the H2OFrame containing the infogram data from xval holdout dataset.")

        rel_cmi_frame_names = rel_cmi_frame.names
        x_label = rel_cmi_frame_names[3]
        y_label = rel_cmi_frame_names[4]
        ig_x_column = 3
        ig_y_column = 4
        index_of_admissible = 1
        features_column = 0
        if self.actual_params['protected_columns'] == None:
            x_thresh = self.actual_params['total_information_threshold']
            y_thresh = self.actual_params['net_information_threshold']
        else:
            x_thresh = self.actual_params["relevance_index_threshold"]
            y_thresh = self.actual_params["safety_index_threshold"]
        
        xmax=1.1
        ymax=1.1

        X = np.array(rel_cmi_frame[ig_x_column].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
        Y = np.array(rel_cmi_frame[ig_y_column].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
        features = np.array(rel_cmi_frame[features_column].as_data_frame(header=False, use_pandas=False)).reshape((-1,))
        admissible = np.array(rel_cmi_frame[index_of_admissible].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
        mask = admissible > 0
        
        if valid:
            X_valid = np.array(rel_cmi_frame_valid[ig_x_column].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
            Y_valid = np.array(rel_cmi_frame_valid[ig_y_column].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
            features_valid = np.array(rel_cmi_frame_valid[features_column].as_data_frame(header=False, use_pandas=False)).reshape((-1,))
            admissible_valid = np.array(rel_cmi_frame_valid[index_of_admissible].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
            mask_valid = admissible_valid > 0       
        
        if xval:
            X_xval = np.array(rel_cmi_frame_xval[ig_x_column].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
            Y_xval = np.array(rel_cmi_frame_xval[ig_y_column].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
            features_xval = np.array(rel_cmi_frame_xval[features_column].as_data_frame(header=False, use_pandas=False)).reshape((-1,))
            admissible_xval = np.array(rel_cmi_frame_xval[index_of_admissible].as_data_frame(header=False, use_pandas=False)).astype(float).reshape((-1,))
            mask_xval = admissible_xval > 0

        plt.figure(figsize=figsize)
        plt.grid(True)
        plt.scatter(X, Y, zorder=10, c=np.where(mask, "black", "gray"), label="training data")
        if valid:
            plt.scatter(X_valid, Y_valid, zorder=10, marker=",", c=np.where(mask_valid, "black", "gray"), label="validation data")
        if xval:
            plt.scatter(X_xval, Y_xval, zorder=10, marker="v", c=np.where(mask_xval, "black", "gray"), label="xval holdout data")
        if legend_on:
            plt.legend(loc=2, fancybox=True, framealpha=0.5)
        plt.hlines(y_thresh, xmin=x_thresh, xmax=xmax, colors="red", linestyle="dashed")
        plt.vlines(x_thresh, ymin=y_thresh, ymax=ymax, colors="red", linestyle="dashed")
        plt.gca().add_collection(polycoll(verts=[[(0,0), (0, ymax), (x_thresh, ymax), (x_thresh, y_thresh), (xmax, y_thresh), (xmax, 0)]],
                                                color="#CC663E", alpha=0.1, zorder=5))
        
        for i in mask.nonzero()[0]:
            plt.annotate(features[i], (X[i], Y[i]), xytext=(0, -10), textcoords="offset points",
                         horizontalalignment='center', verticalalignment='top', color="blue")
        
        if valid:
            for i in mask_valid.nonzero()[0]:
                plt.annotate(features_valid[i], (X_valid[i], Y_valid[i]), xytext=(0, -10), textcoords="offset points",
                             horizontalalignment='center', verticalalignment='top', color="magenta")

        if xval:
            for i in mask_xval.nonzero()[0]:
                plt.annotate(features_xval[i], (X_xval[i], Y_xval[i]), xytext=(0, -10), textcoords="offset points",
                             horizontalalignment='center', verticalalignment='top', color="green")
        
        plt.xlim(0, 1.05)
        plt.ylim(0, 1.05)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        fig = plt.gcf()
        if not server:
            plt.show()
        return decorate_plot_result(figure=fig)
        
    def get_admissible_score_frame(self, valid=False, xval=False):
        """
        Retreive admissible score frame which includes relevance and CMI information in an H2OFrame for training dataset by default
        :param valid: return infogram info on validation dataset if True
        :param xval: return infogram info on cross-validation hold outs if True
        :return: H2OFrame
        """
        keyString = self._model_json["output"]["admissible_score_key"]
        if (valid):
            keyString = self._model_json["output"]["admissible_score_key_valid"]
        elif (xval):
            keyString = self._model_json["output"]["admissible_score_key_xval"]
            
        if keyString is None:
            return None
        else:
            return h2o.get_frame(keyString['name'])

    def get_admissible_features(self):
        """
        :return: a list of predictor that are considered admissible
        """
        if self._model_json["output"]["admissible_features"] is None:
            return None
        else:
            return self._model_json["output"]["admissible_features"]

    def get_admissible_relevance(self):
        """
        :return: a list of relevance (variable importance) for admissible attributes
        """
        if self._model_json["output"]["admissible_relevance"] is None:
            return None
        else:
            return self._model_json["output"]["admissible_relevance"]

    def get_admissible_cmi(self):
        """
        :return: a list of the normalized CMI of admissible attributes
        """
        if self._model_json["output"]["admissible_cmi"] is None:
            return None
        else:
            return self._model_json["output"]["admissible_cmi"]

    def get_admissible_cmi_raw(self):
        """
        :return: a list of raw cmi of admissible attributes 
        """
        if self._model_json["output"]["admissible_cmi_raw"] is None:
            return None
        else:
            return self._model_json["output"]["admissible_cmi_raw"]

    def get_all_predictor_relevance(self):
        """
        Get relevance of all predictors
        :return: two tuples, first one is predictor names and second one is relevance
        """
        if self._model_json["output"]["all_predictor_names"] is None:
            return None
        else:
            return self._model_json["output"]["all_predictor_names"], self._model_json["output"]["relevance"]

    def get_all_predictor_cmi(self):
        """
        Get normalized CMI of all predictors.
        :return: two tuples, first one is predictor names and second one is cmi
        """
        if self._model_json["output"]["all_predictor_names"] is None:
            return None
        else:
            return self._model_json["output"]["all_predictor_names"], self._model_json["output"]["cmi"]

    def get_all_predictor_cmi_raw(self):
        """
        Get raw CMI of all predictors.
        :return: two tuples, first one is predictor names and second one is cmi
        """
        if self._model_json["output"]["all_predictor_names"] is None:
            return None
        else:
            return self._model_json["output"]["all_predictor_names"], self._model_json["output"]["cmi_raw"]
        
    # Override train method to support infogram needs
    def train(self, x=None, y=None, training_frame=None, verbose=False, **kwargs):
        sup = super(self.__class__, self)
        
        def extend_parms(parms):  # add parameter checks specific to infogram
            if parms["data_fraction"] is not None:
                assert_is_type(parms["data_fraction"], numeric)
                assert parms["data_fraction"] > 0 and parms["data_fraction"] <= 1, "data_fraction should exceed 0" \
                                                                                   " and <= 1."
        
        parms = sup._make_parms(x,y,training_frame, extend_parms_fn = extend_parms, **kwargs)

        sup._train(parms, verbose=verbose)
        # can probably get rid of model attributes that Erin does not want here
        return self

extensions = dict(
    __imports__="""
import ast
import json
import warnings
import h2o
from h2o.utils.shared_utils import can_use_numpy
from h2o.utils.typechecks import is_type
from h2o.plot import get_matplotlib_pyplot, decorate_plot_result, get_polycollection
""",
    __class__=class_extensions
)
       
overrides = dict(
    algorithm_params=dict(
        getter="""
if self._parms.get("{sname}") != None:
    algorithm_params_dict =  ast.literal_eval(self._parms.get("{sname}"))
    for k in algorithm_params_dict:
        if len(algorithm_params_dict[k]) == 1: #single parameter
            algorithm_params_dict[k] = algorithm_params_dict[k][0]
    return algorithm_params_dict
else:
    return self._parms.get("{sname}")
""",
        setter="""
assert_is_type({pname}, None, {ptype})
if {pname} is not None and {pname} != "":
    for k in {pname}:
        if ("[" and "]") not in str(algorithm_params[k]):
            algorithm_params[k] = [algorithm_params[k]]
    self._parms["{sname}"] = str(json.dumps({pname}))
else:
    self._parms["{sname}"] = None
"""
    ),
    relevance_index_threshold=dict(
        setter="""
if relevance_index_threshold <= -1: # not set
    if self._parms["protected_columns"] is not None:    # fair infogram
        self._parms["relevance_index_threshold"]=0.1
else: # it is set
    if self._parms["protected_columns"] is not None:    # fair infogram
        self._parms["relevance_index_threshold"] = relevance_index_threshold
    else: # core infogram should not have been set
        warnings.warn("Should not set relevance_index_threshold for core infogram runs.  Set total_information_threshold instead.  Using default of 0.1 if not set", RuntimeWarning)
"""
    ),
    safety_index_threshold=dict(
        setter="""
if safety_index_threshold <= -1: # not set
    if self._parms["protected_columns"] is not None:
        self._parms["safety_index_threshold"]=0.1
else: # it is set
    if self._parms["protected_columns"] is not None: # fair infogram
        self._parms["safety_index_threshold"] = safety_index_threshold
    else: # core infogram should not have been set
        warnings.warn("Should not set safety_index_threshold for core infogram runs.  Set net_information_threshold instead.  Using default of 0.1 if not set", RuntimeWarning)
"""
    ),
    net_information_threshold=dict(
        setter="""
if net_information_threshold <= -1: # not set
    if self._parms["protected_columns"] is None:
        self._parms["net_information_threshold"]=0.1
else:  # set
    if self._parms["protected_columns"] is not None: # fair infogram
        warnings.warn("Should not set net_information_threshold for fair infogram runs.  Set safety_index_threshold instead.  Using default of 0.1 if not set", RuntimeWarning)
    else:
        self._parms["net_information_threshold"]=net_information_threshold
"""
    ),
    total_information_threshold=dict(
        setter="""
if total_information_threshold <= -1: # not set
    if self._parms["protected_columns"] is None:
        self._parms["total_information_threshold"] = 0.1
else:
    if self._parms["protected_columns"] is not None: # fair infogram
        warnings.warn("Should not set total_information_threshold for fair infogram runs.  Set relevance_index_threshold instead.  Using default of 0.1 if not set", RuntimeWarning)
    else:
        self._parms["total_information_threshold"] = total_information_threshold
"""
    )
)

doc = dict(
    __class__="""
The infogram is a graphical information-theoretic interpretability tool which allows the user to quickly spot the core, decision-making variables 
that uniquely and safely drive the response, in supervised classification problems. The infogram can significantly cut down the number of predictors needed to build 
a model by identifying only the most valuable, admissible features. When protected variables such as race or gender are present in the data, the admissibility 
of a variable is determined by a safety and relevancy index, and thus serves as a diagnostic tool for fairness. The safety of each feature can be quantified and 
variables that are unsafe will be considered inadmissible. Models built using only admissible features will naturally be more interpretable, given the reduced 
feature set.  Admissible models are also less susceptible to overfitting and train faster, while providing similar accuracy as models built using all available features.
"""
)
